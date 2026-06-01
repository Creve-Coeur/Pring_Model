# -*- coding: utf-8 -*-
from __future__ import annotations

import fnmatch
import getpass
import json
import os
import posixpath
import stat
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Iterable
from urllib.parse import quote


LOCAL_CONFIG_FILE = Path(__file__).resolve().with_name(".tencent_deploy.local.json")

DEFAULT_HOST = "124.222.218.38"
DEFAULT_PORT = 22
DEFAULT_USER = "root"
DEFAULT_REMOTE_ROOT = "/data/www/Asset_Class"
DEFAULT_SITE_URL = "http://124.222.218.38/Asset_Class/"
DEFAULT_KEY_PATH = Path.home() / ".ssh" / "id_ed25519"

DEFAULT_EXCLUDE_PATTERNS = [
    ".git",
    ".git/**",
    ".git_backup",
    ".git_backup/**",
    ".netlify",
    ".netlify/**",
    "__pycache__",
    "__pycache__/**",
    "*.pyc",
    "*.pyo",
    "*.py",
    "*.bat",
    "*.ps1",
    "*.md",
    ".gitignore",
    ".DS_Store",
    "Thumbs.db",
    ".tencent_deploy.local.json",
    "tencent_cloud_deploy.py",
    "同步网站到腾讯云.py",
    "同步网站到GitHub.py",
    "一键同步到GitHub.bat",
    "组合介绍/build_report_site_腾讯云.py",
    "组合实盘追踪/获取每日持仓情况_ver4.0_腾讯云.py",
]


@dataclass
class TencentDeployConfig:
    host: str = DEFAULT_HOST
    port: int = DEFAULT_PORT
    username: str = DEFAULT_USER
    remote_root: str = DEFAULT_REMOTE_ROOT
    site_url: str = DEFAULT_SITE_URL
    key_path: Path | None = DEFAULT_KEY_PATH
    passphrase: str | None = None
    password: str | None = None


@dataclass
class TencentDeployResult:
    local_path: str
    remote_path: str
    url: str
    uploaded: int
    skipped: int
    deleted: int

    def as_dict(self) -> dict[str, object]:
        return {
            "local_path": self.local_path,
            "remote_path": self.remote_path,
            "url": self.url,
            "uploaded": self.uploaded,
            "skipped": self.skipped,
            "deleted": self.deleted,
        }


def load_config(prompt_for_passphrase: bool = True) -> TencentDeployConfig:
    local_config = _read_local_config()

    key_path_text = _first_value(
        os.environ.get("TENCENT_SSH_KEY"),
        local_config.get("key_path"),
        str(DEFAULT_KEY_PATH),
    )
    key_path = Path(key_path_text).expanduser() if key_path_text else None

    config = TencentDeployConfig(
        host=str(_first_value(os.environ.get("TENCENT_CLOUD_HOST"), local_config.get("host"), DEFAULT_HOST)),
        port=int(_first_value(os.environ.get("TENCENT_CLOUD_PORT"), local_config.get("port"), DEFAULT_PORT)),
        username=str(_first_value(os.environ.get("TENCENT_CLOUD_USER"), local_config.get("username"), DEFAULT_USER)),
        remote_root=str(
            _first_value(os.environ.get("TENCENT_REMOTE_ROOT"), local_config.get("remote_root"), DEFAULT_REMOTE_ROOT)
        ),
        site_url=str(_first_value(os.environ.get("TENCENT_SITE_URL"), local_config.get("site_url"), DEFAULT_SITE_URL)),
        key_path=key_path,
        passphrase=_first_value(os.environ.get("TENCENT_SSH_PASSPHRASE"), local_config.get("passphrase")),
        password=_first_value(os.environ.get("TENCENT_SSH_PASSWORD"), local_config.get("password")),
    )

    if prompt_for_passphrase and config.passphrase is None and config.password is None:
        config.passphrase = _prompt_secret("请输入腾讯云 SSH 私钥密码（输入时不会显示，直接回车则跳过）：")

    config.remote_root = _normalize_remote_path(config.remote_root)
    return config


def deploy_path_to_tencent(
    local_path: str | os.PathLike[str],
    remote_subdir: str = "",
    *,
    exclude_patterns: Iterable[str] | None = None,
    preserve_patterns: Iterable[str] | None = None,
    prune: bool = True,
    prompt_for_passphrase: bool = True,
) -> dict[str, object]:
    config = load_config(prompt_for_passphrase=prompt_for_passphrase)
    local_root = Path(local_path).resolve()
    if not local_root.exists():
        raise FileNotFoundError(f"本地路径不存在：{local_root}")
    if not local_root.is_dir():
        raise NotADirectoryError(f"当前只支持部署文件夹：{local_root}")

    remote_target = _remote_join(config.remote_root, remote_subdir)
    _assert_remote_inside(config.remote_root, remote_target)

    excludes = list(DEFAULT_EXCLUDE_PATTERNS)
    if exclude_patterns:
        excludes.extend(exclude_patterns)
    preserves = list(preserve_patterns or [])

    print(f"准备部署到腾讯云：{config.username}@{config.host}:{remote_target}")
    client = _connect(config)
    uploaded = 0
    skipped = 0
    deleted = 0

    try:
        with client.open_sftp() as sftp:
            _ensure_remote_dir(sftp, remote_target)
            wanted_files, wanted_dirs = _collect_wanted_paths(local_root, excludes)

            for rel_dir in sorted(wanted_dirs):
                _ensure_remote_dir(sftp, _remote_join(remote_target, "" if rel_dir == "." else rel_dir))

            for rel_file in sorted(wanted_files):
                local_file = local_root / Path(rel_file)
                remote_file = _remote_join(remote_target, rel_file)
                _assert_remote_inside(remote_target, remote_file)
                _ensure_remote_dir(sftp, posixpath.dirname(remote_file))
                if _remote_file_is_current(sftp, remote_file, local_file):
                    skipped += 1
                    continue
                sftp.put(str(local_file), remote_file)
                mtime = int(local_file.stat().st_mtime)
                sftp.utime(remote_file, (mtime, mtime))
                uploaded += 1

            if prune:
                deleted = _prune_remote(sftp, remote_target, wanted_files, wanted_dirs, preserves)
    finally:
        client.close()

    result = TencentDeployResult(
        local_path=str(local_root),
        remote_path=remote_target,
        url=_build_url(config.site_url, remote_subdir),
        uploaded=uploaded,
        skipped=skipped,
        deleted=deleted,
    )
    print(
        "腾讯云部署完成："
        f"上传 {result.uploaded} 个，跳过 {result.skipped} 个，清理 {result.deleted} 个。"
    )
    print(f"访问地址：{result.url}")
    return result.as_dict()


def _read_local_config() -> dict[str, object]:
    if not LOCAL_CONFIG_FILE.exists():
        return {}
    with LOCAL_CONFIG_FILE.open("r", encoding="utf-8") as file:
        data = json.load(file)
    if not isinstance(data, dict):
        raise ValueError(f"本地腾讯云配置格式不正确：{LOCAL_CONFIG_FILE}")
    return data


def _first_value(*values):
    for value in values:
        if value is not None:
            return value
    return None


def _prompt_secret(prompt: str) -> str | None:
    if os.environ.get("TENCENT_DEPLOY_NO_PROMPT") == "1":
        return None
    try:
        value = getpass.getpass(prompt)
    except Exception:
        return None
    return value or None


def _connect(config: TencentDeployConfig):
    try:
        import paramiko
    except ImportError as exc:
        raise RuntimeError("当前 Python 环境缺少 paramiko，请先安装后再部署。") from exc

    key_filename = None
    if config.key_path and config.key_path.exists():
        key_filename = str(config.key_path)

    def make_client():
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        return client

    client = make_client()
    try:
        client.connect(
            hostname=config.host,
            port=config.port,
            username=config.username,
            key_filename=key_filename,
            passphrase=config.passphrase,
            password=config.password,
            allow_agent=True,
            look_for_keys=True,
            timeout=30,
            banner_timeout=30,
            auth_timeout=30,
        )
    except Exception as first_exc:
        client.close()
        password_fallback = config.password or config.passphrase
        if password_fallback:
            password_client = make_client()
            try:
                password_client.connect(
                    hostname=config.host,
                    port=config.port,
                    username=config.username,
                    password=password_fallback,
                    allow_agent=False,
                    look_for_keys=False,
                    timeout=30,
                    banner_timeout=30,
                    auth_timeout=30,
                )
                print("已使用 SSH 密码方式连接腾讯云。")
                return password_client
            except Exception:
                password_client.close()

        hint = (
            "连接腾讯云失败。请确认私钥已放在 ~/.ssh/id_ed25519，"
            "或用 TENCENT_SSH_KEY 指定私钥路径；如果私钥有密码，"
            "可用 TENCENT_SSH_PASSPHRASE 或 .tencent_deploy.local.json 提前保存。"
        )
        raise RuntimeError(f"{hint} 原始错误：{first_exc}") from first_exc

    return client


def _collect_wanted_paths(local_root: Path, exclude_patterns: list[str]) -> tuple[set[str], set[str]]:
    wanted_files: set[str] = set()
    wanted_dirs: set[str] = {"."}

    for path in local_root.rglob("*"):
        rel = path.relative_to(local_root)
        if _matches_any(rel.as_posix(), rel.name, exclude_patterns) or _has_excluded_part(rel):
            continue
        rel_text = rel.as_posix()
        if path.is_dir():
            wanted_dirs.add(rel_text)
        elif path.is_file():
            wanted_files.add(rel_text)
            wanted_dirs.update(_parent_dirs(rel_text))

    return wanted_files, wanted_dirs


def _has_excluded_part(rel: Path) -> bool:
    return any(part in {".git", ".git_backup", ".netlify", "__pycache__"} for part in rel.parts)


def _parent_dirs(rel_text: str) -> set[str]:
    parts = rel_text.split("/")[:-1]
    dirs = {"."}
    current = ""
    for part in parts:
        current = f"{current}/{part}" if current else part
        dirs.add(current)
    return dirs


def _matches_any(rel_text: str, name: str, patterns: Iterable[str]) -> bool:
    rel_text = PurePosixPath(rel_text).as_posix()
    return any(fnmatch.fnmatch(rel_text, pattern) or fnmatch.fnmatch(name, pattern) for pattern in patterns)


def _normalize_remote_path(path: str) -> str:
    normalized = posixpath.normpath(path.replace("\\", "/"))
    if not normalized.startswith("/"):
        raise ValueError(f"远程路径必须是绝对路径：{path}")
    return normalized


def _remote_join(root: str, rel: str) -> str:
    if not rel:
        return _normalize_remote_path(root)
    return _normalize_remote_path(posixpath.join(root, rel.replace("\\", "/")))


def _assert_remote_inside(root: str, candidate: str) -> None:
    root = _normalize_remote_path(root).rstrip("/")
    candidate = _normalize_remote_path(candidate)
    if candidate != root and not candidate.startswith(root + "/"):
        raise RuntimeError(f"安全检查失败，拒绝操作目标目录之外的路径：{candidate}")


def _ensure_remote_dir(sftp, remote_dir: str) -> None:
    remote_dir = _normalize_remote_path(remote_dir)
    current = "/"
    for part in [item for item in remote_dir.split("/") if item]:
        current = posixpath.join(current, part)
        try:
            attrs = sftp.stat(current)
            if not stat.S_ISDIR(attrs.st_mode):
                raise RuntimeError(f"远程路径不是目录：{current}")
        except OSError:
            sftp.mkdir(current)


def _remote_file_is_current(sftp, remote_file: str, local_file: Path) -> bool:
    try:
        attrs = sftp.stat(remote_file)
    except OSError:
        return False
    local_stat = local_file.stat()
    return attrs.st_size == local_stat.st_size and abs(int(attrs.st_mtime) - int(local_stat.st_mtime)) <= 2


def _remote_walk(sftp, remote_root: str):
    try:
        entries = sftp.listdir_attr(remote_root)
    except OSError:
        return

    for entry in entries:
        name = entry.filename
        if name in {".", ".."}:
            continue
        remote_path = posixpath.join(remote_root, name)
        if stat.S_ISDIR(entry.st_mode):
            yield "dir", remote_path
            yield from _remote_walk(sftp, remote_path)
        else:
            yield "file", remote_path


def _prune_remote(
    sftp,
    remote_target: str,
    wanted_files: set[str],
    wanted_dirs: set[str],
    preserve_patterns: list[str],
) -> int:
    deleted = 0
    remote_entries = list(_remote_walk(sftp, remote_target) or [])

    for kind, remote_path in sorted(remote_entries, reverse=True):
        if kind != "file":
            continue
        rel = posixpath.relpath(remote_path, remote_target)
        if rel == "." or _matches_any(rel, posixpath.basename(rel), preserve_patterns):
            continue
        if rel not in wanted_files:
            _assert_remote_inside(remote_target, remote_path)
            sftp.remove(remote_path)
            deleted += 1

    for kind, remote_path in sorted(remote_entries, reverse=True):
        if kind != "dir":
            continue
        rel = posixpath.relpath(remote_path, remote_target)
        if rel == "." or _matches_any(rel, posixpath.basename(rel), preserve_patterns):
            continue
        if rel not in wanted_dirs:
            try:
                _assert_remote_inside(remote_target, remote_path)
                sftp.rmdir(remote_path)
                deleted += 1
            except OSError:
                pass

    return deleted


def _build_url(base_url: str, subdir: str) -> str:
    base = base_url.rstrip("/") + "/"
    clean_subdir = subdir.strip("/").replace("\\", "/")
    if not clean_subdir:
        return base
    encoded = "/".join(quote(part) for part in clean_subdir.split("/") if part)
    return base + encoded + "/"
