#%% Step 1: 实盘化全局数据准备 —— 本地 Excel 极速直读版
import pandas as pd
import datetime
import warnings
import sys
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.ticker import FuncFormatter

warnings.filterwarnings('ignore')

print("【Step 1】开始初始化：正在直接读取本地 Excel 历史数据文件...")

start_fetch_date = "2022-10-01" 
print(f"⚡ 本地直读模式：统一从 {start_fetch_date} 起截取数据...")

# ================= 1.1 读取普林格宏观调仓文件 =================
try:
    pring_df = pd.read_excel(r'C:\Users\Coeur\Desktop\红筹投资\组合构建\组合的诞生\最新普林格调仓明细_至202603(含异象处理_实盘版).xlsx', sheet_name='Sheet1')
    print("✅ 成功读取：普林格宏观调仓明细表")
except Exception as e:
    print(f"❌ 关键宏观文件读取失败，程序强制中断: {e}")
    sys.exit()

# ================= 1.2 读取并清洗本地 Excel 文件 =================
try:
    # 直接使用绝对路径或相对路径读取原始 Excel 文件，并指定 Sheet 名
    # 提示：同花顺导出的数据，Sheet 名默认就是 '收盘价(元)'
    df1 = pd.read_excel(r'C:\Users\Coeur\Desktop\红筹投资\组合构建\组合的诞生\1-5.xlsx', sheet_name='收盘价(元)')
    df2 = pd.read_excel(r'C:\Users\Coeur\Desktop\红筹投资\组合构建\组合的诞生\6-10.xlsx', sheet_name='收盘价(元)')
    
    # 优雅清洗法：强制转换为 datetime。同花顺文件底部的"数据来源:同花顺"等中文文本
    # 在强转时会因为 errors='coerce' 变成 NaT，随后直接 dropna 剔除即可，完美兼容 Excel 格式
    df1['日期'] = pd.to_datetime(df1['日期'], errors='coerce')
    df2['日期'] = pd.to_datetime(df2['日期'], errors='coerce')
    
    df1 = df1.dropna(subset=['日期']).copy()
    df2 = df2.dropna(subset=['日期']).copy()
    
    # 按日期合并这两份表
    df = pd.merge(df1, df2, on='日期', how='outer')
    df = df.set_index('日期').sort_index()
    
    # 强制转为数值 (跳过 ffill，以便下一步准确寻找真实的上市首日)
    for col in df.columns:
        df[col] = pd.to_numeric(df[col], errors='coerce')
    
    # 清除全空的行
    df = df.dropna(how='all')
    
    # 将长列名映射为标准名称
    rename_map = {
        '沪深300ETF华泰柏瑞': '沪深300ETF',
        '中证1000ETF南方': '中证1000ETF',
        '创业板ETF易方达': '创业板指ETF',
        '恒生科技ETF易方达': '恒生科技ETF',
        '可转债ETF博时': '博时可转债ETF',
        '有色ETF大成': '大成有色ETF',
        '黄金ETF华安': '华安黄金ETF',
        '能源化工ETF建信': '建信能化ETF',
        '豆粕ETF华夏': '华夏豆粕ETF',
        '中欧纯债LOF': '中欧纯债LOF'   
    }
    df = df.rename(columns=rename_map)
    print("✅ 成功加载并合并本地 Excel 历史数据文件！\n")
    
except Exception as e:
    print(f"❌ 读取本地 Excel 文件失败，报错: {e}")
    sys.exit()

# ================= 1.3 木桶效应扫描：提取最短板起始日 =================
print("正在逐一扫描底层资产的有效数据起始日...")
etf_start_dates = {}

for name in df.columns:
    # 自动找到该列第一个非 NaN 值的日期
    first_valid_date = df[name].first_valid_index()
    etf_start_dates[name] = first_valid_date
    if pd.notna(first_valid_date):
        print(f"  - {name:<10} 数据起始: {first_valid_date.strftime('%Y-%m-%d')}")
    else:
        print(f"  - ❌ {name:<10} 未找到有效数据！")

latest_start_date = max(etf_start_dates.values())

print("\n" + "="*60)
print(f"🔍 【木桶短板扫描完成】")
latest_etfs = [name for name, date in etf_start_dates.items() if date == latest_start_date]
print(f"最晚出现数据的底层标的为：{', '.join(latest_etfs)}")
print(f"🎯 统一实盘回测起点将被强制对齐至: 【{latest_start_date.strftime('%Y-%m-%d')}】")
print("="*60 + "\n")

# ================= 1.4 对齐数据与计算收益率 =================
# 对齐前，先执行前向填充 (ffill) 修复中间因停牌等情况产生的缺失值
df = df.ffill()

# 强制截断最晚起始日之前的所有无用数据
prices_all = df[df.index >= latest_start_date]

# 计算日频收益率
ret_all = prices_all.pct_change().fillna(0)

print(f"🎉 Step 1 本地数据准备完毕！共计获取 {len(ret_all)} 个交易日数据。准备进入逻辑运算...\n")
    
#%% Step 2: 实盘化四核引擎构建与宏观权重对齐
print("\n========== 开始执行 Step 2: 构建实盘等权引擎与对齐宏观权重 ==========")

# 1. 定义四大核心引擎的实盘 ETF 成分
eq_etfs = ['沪深300ETF', '中证1000ETF', '创业板指ETF', '恒生科技ETF']
com_etfs = ['大成有色ETF', '华安黄金ETF', '建信能化ETF', '华夏豆粕ETF']
cb_etf = '博时可转债ETF'
cdb_etf = '中欧纯债LOF'  # 更新底仓名称

# 2. 生成引擎级日频收益率 (等权配置)
print("正在合成【股票端】实盘等权宽基引擎 (沪深300/中证1000/创业板/恒生科技)...")
r_eq_daily = ret_all[eq_etfs].mean(axis=1)

print("正在合成【商品端】实盘等权商品引擎 (有色/黄金/能化/豆粕)...")
r_com_daily = ret_all[com_etfs].mean(axis=1)

# 转债与纯债直接取用单只收益率
r_cb_daily = ret_all[cb_etf]
r_cdb_daily = ret_all[cdb_etf]

# 为后续均线计算准备净值序列
nav_eq = (1 + r_eq_daily).cumprod()
nav_com = (1 + r_com_daily).cumprod()

# 3. 处理普林格宏观权重
print("正在抽取并对齐普林格宏观权重...")
pring_df['调仓日期'] = pd.to_datetime(pring_df['调仓日期'])

weights_df = pring_df.set_index('调仓日期')[['沪深300指数', '南华期货:商品指数', '中证基金指数:货币基金', '中证全债指数']]
trading_days = ret_all.index
all_dates = sorted(list(set(trading_days) | set(weights_df.index)))
weights_daily_live = weights_df.reindex(all_dates).ffill().loc[trading_days]

print(f"✅ Step 2 数据合成完毕！实盘引擎底座已就绪，起始日：{trading_days[0].strftime('%Y-%m-%d')}。")

#%% Step 3: 实盘化核心策略大乱斗 —— 纯粹 MA20 基准版与全景可视化
# 设置中文字体，防止图表乱码
plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei']
plt.rcParams['axes.unicode_minus'] = False

print("\n========== 开始执行 Step 3: 【实盘四核防御形态】纯粹 MA20 基准版 ==========")

# --- 1. 底层标尺与均线准备 ---
hs300_ret = ret_all['沪深300ETF']
nav_hs300 = (1 + hs300_ret).cumprod()

nav_eq_ma20 = nav_eq.rolling(window=20).mean()
nav_com_ma20 = nav_com.rolling(window=20).mean()

print(f"✅ 避险目标锁定：当触发标准 MA20 跌破时，资金将全额撤离至 [{cdb_etf}]")

# --- 2. 策略回溯运算 ---
dates_all = trading_days
ret_A = []  
ret_C = []  

trades_C_eq, trades_C_com = 0, 0
prev_esc_C_eq, prev_esc_C_com = False, False

daily_active_assets = {}  
is_eq_escape_daily, is_com_escape_daily = {}, {}
hist_w_eq, hist_w_com, hist_w_cb, hist_w_cdb = [], [], [], []

for i, d in enumerate(dates_all):
    w_eq = weights_daily_live['沪深300指数'].loc[d] if pd.notna(weights_daily_live['沪深300指数'].loc[d]) else 0.0
    w_com = weights_daily_live['南华期货:商品指数'].loc[d] if pd.notna(weights_daily_live['南华期货:商品指数'].loc[d]) else 0.0
    w_bond_total = (
        (weights_daily_live['中证基金指数:货币基金'] + weights_daily_live['中证全债指数']).loc[d]
        if pd.notna((weights_daily_live['中证基金指数:货币基金'] + weights_daily_live['中证全债指数']).loc[d])
        else 0.0
    )

    w_cdb_base = min(0.10, w_bond_total)
    w_cb_base = max(0.0, w_bond_total - 0.10)

    is_eq_heavy = w_eq > 0.65
    is_com_heavy = w_com > 0.65

    prev_date = dates_all[i - 1] if i > 0 else dates_all[0]

    e_m_cond = nav_eq.loc[prev_date] >= nav_eq_ma20.loc[prev_date] if pd.notna(nav_eq_ma20.loc[prev_date]) else True
    c_m_cond = nav_com.loc[prev_date] >= nav_com_ma20.loc[prev_date] if pd.notna(nav_com_ma20.loc[prev_date]) else True

    r_e = r_eq_daily.loc[d]
    r_c = r_com_daily.loc[d]
    r_cb = r_cb_daily.loc[d]
    r_cdb = r_cdb_daily.loc[d]

    act_eq = e_m_cond if is_eq_heavy else True
    act_com = c_m_cond if is_com_heavy else True

    if (not act_eq) != prev_esc_C_eq:
        trades_C_eq += 1
        prev_esc_C_eq = (not act_eq)
    if (not act_com) != prev_esc_C_com:
        trades_C_com += 1
        prev_esc_C_com = (not act_com)

    final_w_eq = w_eq if act_eq else 0.0
    final_w_com = w_com if act_com else 0.0
    final_w_cb = w_cb_base
    final_w_cdb = w_cdb_base + (w_eq - final_w_eq) + (w_com - final_w_com)

    ret_C.append(final_w_eq * r_e + final_w_com * r_c + final_w_cb * r_cb + final_w_cdb * r_cdb)
    ret_A.append(w_eq * r_e + w_com * r_c + w_cb_base * r_cb + w_cdb_base * r_cdb)

    active_assets = []
    if final_w_eq > 0: active_assets.append('【股】宽基等权ETF')
    if final_w_com > 0: active_assets.append('【商】商品等权ETF')
    daily_active_assets[d] = active_assets
    is_eq_escape_daily[d] = not act_eq
    is_com_escape_daily[d] = not act_com
    
    hist_w_eq.append(final_w_eq * 100)
    hist_w_com.append(final_w_com * 100)
    hist_w_cb.append(final_w_cb * 100)
    hist_w_cdb.append(final_w_cdb * 100)

# --- 3. 绩效与绘图 ---
nav_A = (1 + pd.Series(ret_A, index=dates_all)).cumprod()
nav_C = (1 + pd.Series(ret_C, index=dates_all)).cumprod()

def get_metrics(nav, name):
    daily = nav.pct_change().fillna(0)
    ann = nav.iloc[-1] ** (252 / len(nav)) - 1
    mdd = (nav / nav.cummax() - 1).min()
    vol = daily.std() * np.sqrt(252)
    sharpe = (ann - 0.02) / vol if vol != 0 else 0.0
    
    # 新增：计算卡玛比率 (年化收益 / 最大回撤的绝对值)
    calmar = ann / abs(mdd) if mdd != 0 else 0.0
    
    # 修改：在返回的字典中加入波动率和卡玛比率
    return {
        '策略': name, 
        '年化': f"{ann*100:.2f}%", 
        '回撤': f"{mdd*100:.2f}%", 
        '夏普': f"{sharpe:.2f}",
        '波动率': f"{vol*100:.2f}%",   # 新增
        '卡玛比率': f"{calmar:.2f}"    # 新增
    }

print("\n========================= 实盘全景回测：(全量逃逸版) 核心绩效 =========================")
print(pd.DataFrame([
    get_metrics(nav_hs300, "沪深300ETF (大盘基准)"),
    get_metrics(nav_A, "理论原版 (无避险满仓)"),
    get_metrics(nav_C, "实盘四核终极版 (全入纯债底仓)")
]).to_string(index=False))

print("\n正在渲染带季度坐标轴的全景甘特图与资金分布...")
all_labels = []
for assets in daily_active_assets.values():
    for a in assets:
        if a not in all_labels:
            all_labels.append(a)
if '【商】商品等权ETF' in all_labels:
    all_labels.remove('【商】商品等权ETF')
    all_labels.insert(0, '【商】商品等权ETF')
label_y = {l: i for i, l in enumerate(all_labels)}

fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(16, 18), gridspec_kw={'height_ratios': [1.2, 0.8, 1.5]}, sharex=True)

for lbl, y in label_y.items():
    is_in = False
    start = None
    color = 'darkgoldenrod' if '【商】' in lbl else 'limegreen'
    for d in dates_all:
        present = lbl in daily_active_assets[d]
        if present and not is_in:
            is_in = True; start = d
        elif not present and is_in:
            is_in = False
            ax1.broken_barh([(mdates.date2num(start), mdates.date2num(d) - mdates.date2num(start))], (y - 0.3, 0.6), color=color, edgecolor='black', linewidth=0.5)
    if is_in:
        ax1.broken_barh([(mdates.date2num(start), mdates.date2num(dates_all[-1]) - mdates.date2num(start))], (y - 0.3, 0.6), color=color)

for d in dates_all:
    if is_eq_escape_daily[d]: ax1.axvspan(d, d + pd.Timedelta(days=1), color='crimson', alpha=0.15)
    if is_com_escape_daily[d]: ax1.axvspan(d, d + pd.Timedelta(days=1), color='orange', alpha=0.15)

ax1.set_yticks(range(len(all_labels)))
ax1.set_yticklabels(all_labels)
ax1.invert_yaxis()
ax1.set_title('实盘甘特图：主引擎定向避险状态 (红色/橙色背景代表逃逸期)', fontsize=15, fontweight='bold')

y1 = np.array(hist_w_eq)
y2 = y1 + np.array(hist_w_cb)
y3 = y2 + np.array(hist_w_com)
y4 = y3 + np.array(hist_w_cdb)

ax2.fill_between(dates_all, 0,  y1, label='宽基等权ETF(股票)', color='crimson', alpha=0.8, step='post')
ax2.fill_between(dates_all, y1, y2, label='可转债ETF(进攻)', color='darkviolet', alpha=0.8, step='post')
ax2.fill_between(dates_all, y2, y3, label='商品等权ETF', color='darkgoldenrod', alpha=0.8, step='post')
ax2.fill_between(dates_all, y3, y4, label='中欧纯债LOF(蓄水池)', color='steelblue', alpha=0.8, step='post')
ax2.set_ylabel('占比 (%)'); ax2.set_ylim(0, 100); ax2.legend(loc='upper left', ncol=4); ax2.margins(x=0)

ax3.plot(nav_C.index, nav_C, label='实盘四核终极形态 (MA20 避险)', color='crimson', linewidth=3)
ax3.plot(nav_A.index, nav_A, label='理论原版 (无避险)', color='grey', linestyle='--', alpha=0.7)
ax3.plot(nav_hs300.index, nav_hs300, label='沪深300ETF', color='black', linewidth=1, alpha=0.5)
ax3.set_title('实盘对决 (本地源)：不同风控策略下的净值增长曲线', fontsize=15, fontweight='bold')
ax3.legend(loc='upper left'); ax3.grid(True, alpha=0.3)

def quarter_formatter(x, pos):
    try:
        dt = mdates.num2date(x)
        return f"{dt.year}Q{(dt.month - 1) // 3 + 1}"
    except: return ""

ax3.xaxis.set_major_locator(mdates.MonthLocator(bymonth=[1, 4, 7, 10]))
ax3.xaxis.set_major_formatter(FuncFormatter(quarter_formatter))
plt.setp(ax3.get_xticklabels(), rotation=45, ha='right', fontsize=11, fontweight='bold')
plt.tight_layout()
plt.show()

# 为后续归因准备 df_daily
r_eq = pd.Series(r_eq_daily, index=dates_all)
r_com = pd.Series(r_com_daily, index=dates_all)
r_cb = pd.Series(r_cb_daily, index=dates_all)
r_cdb = pd.Series(r_cdb_daily, index=dates_all)

s_w_eq = pd.Series(hist_w_eq, index=dates_all) / 100.0
s_w_com = pd.Series(hist_w_com, index=dates_all) / 100.0
s_w_cb = pd.Series(hist_w_cb, index=dates_all) / 100.0
s_w_cdb = pd.Series(hist_w_cdb, index=dates_all) / 100.0

df_daily = pd.DataFrame({'Eq': s_w_eq * r_eq, 'Com': s_w_com * r_com, 'Cb': s_w_cb * r_cb, 'Cdb': s_w_cdb * r_cdb,
    'Strat': pd.Series(ret_C, index=dates_all), 'HS300': hs300_ret.reindex(dates_all).fillna(0)})
df_daily['Prev_NAV'] = nav_C.shift(1).fillna(1.0)
df_daily['Year'] = df_daily.index.year

#%% Step 4: 实盘化四核防御形态 —— 详细调仓合并日志与精准测算记录 (Excel 导出)
print("\n========== 开始执行 Step 4: 生成【实盘详细调仓记录表】 ==========")

merged_records = []
last_state = None

for i, d in enumerate(dates_all):
    w_eq_macro = weights_daily_live['沪深300指数'].loc[d] if pd.notna(weights_daily_live['沪深300指数'].loc[d]) else 0.0
    w_com_macro = weights_daily_live['南华期货:商品指数'].loc[d] if pd.notna(weights_daily_live['南华期货:商品指数'].loc[d]) else 0.0
    w_bond_total = (
        (weights_daily_live['中证基金指数:货币基金'] + weights_daily_live['中证全债指数']).loc[d]
        if pd.notna((weights_daily_live['中证基金指数:货币基金'] + weights_daily_live['中证全债指数']).loc[d]) else 0.0
    )

    w_cdb_base = min(0.10, w_bond_total)
    w_cb_base = max(0.0, w_bond_total - 0.10)

    is_eq_heavy = w_eq_macro > 0.65
    is_com_heavy = w_com_macro > 0.65

    prev_date = dates_all[i - 1] if i > 0 else dates_all[0]
    
    ma20_eq_val = nav_eq_ma20.loc[prev_date]
    ma20_com_val = nav_com_ma20.loc[prev_date]

    e_m_cond = nav_eq.loc[prev_date] >= ma20_eq_val if pd.notna(ma20_eq_val) else True
    c_m_cond = nav_com.loc[prev_date] >= ma20_com_val if pd.notna(ma20_com_val) else True

    act_eq = e_m_cond if is_eq_heavy else True
    act_com = c_m_cond if is_com_heavy else True

    final_w_eq = w_eq_macro if act_eq else 0.0
    final_w_com = w_com_macro if act_com else 0.0
    final_w_cb = w_cb_base
    final_w_cdb = w_cdb_base + (w_eq_macro - final_w_eq) + (w_com_macro - final_w_com)

    current_sig = (w_eq_macro, w_com_macro, act_eq, act_com)
    date_str = d.strftime('%Y-%m-%d')

    if last_state and current_sig == last_state['sig']:
        merged_records[-1]['结束日期'] = date_str
        merged_records[-1]['交易天数'] += 1
    else:
        reason = []
        is_ma20_triggered = False

        if last_state:
            prev_sig = last_state['sig']
            if current_sig[0] != prev_sig[0] or current_sig[1] != prev_sig[1]:
                reason.append("宏观季度调仓")
            if current_sig[2] != prev_sig[2]:
                if not current_sig[2]: reason.append("🔴股端击穿MA20-撤退至纯债")
                else: reason.append("🟢股端收复MA20-买回宽基")
                is_ma20_triggered = True
            if current_sig[3] != prev_sig[3]:
                if not current_sig[3]: reason.append("🟠商端击穿MA20-撤退至纯债")
                else: reason.append("🟡商端收复MA20-买回商品")
                is_ma20_triggered = True
        else:
            reason.append("初始建仓")

        reason_str = " + ".join(reason)

        price_dict = {
            '股端MA20触发价': '-', '商端MA20触发价': '-',
            '【股】合成价格': '-', '【商】合成价格': '-',
            '沪深300(510300.SH)': '-', '中证1000(512100.SH)': '-', 
            '创业板指(159915.SZ)': '-', '恒生科技(513010.SH)': '-',
            '有色ETF(159980.SZ)': '-', '黄金ETF(518880.SH)': '-', 
            '能化ETF(159981.SZ)': '-', '豆粕ETF(159985.SZ)': '-',
            '博时可转债(511380.SH)': '-', '中欧纯债LOF(166016.SZ)': '-'
        }

        if is_ma20_triggered or not last_state or "宏观季度调仓" in reason_str: 
            price_dict['股端MA20触发价'] = f"{ma20_eq_val:.4f}" if is_eq_heavy and pd.notna(ma20_eq_val) else "不适用"
            price_dict['商端MA20触发价'] = f"{ma20_com_val:.4f}" if is_com_heavy and pd.notna(ma20_com_val) else "不适用"
            price_dict['【股】合成价格'] = f"{nav_eq.loc[d]:.4f}"
            price_dict['【商】合成价格'] = f"{nav_com.loc[d]:.4f}"
            price_dict['沪深300(510300.SH)'] = f"{prices_all.loc[d, '沪深300ETF']:.3f}"
            price_dict['中证1000(512100.SH)'] = f"{prices_all.loc[d, '中证1000ETF']:.3f}"
            price_dict['创业板指(159915.SZ)'] = f"{prices_all.loc[d, '创业板指ETF']:.3f}"
            price_dict['恒生科技(513010.SH)'] = f"{prices_all.loc[d, '恒生科技ETF']:.3f}"
            price_dict['有色ETF(159980.SZ)'] = f"{prices_all.loc[d, '大成有色ETF']:.3f}"
            price_dict['黄金ETF(518880.SH)'] = f"{prices_all.loc[d, '华安黄金ETF']:.3f}"
            price_dict['能化ETF(159981.SZ)'] = f"{prices_all.loc[d, '建信能化ETF']:.3f}"
            price_dict['豆粕ETF(159985.SZ)'] = f"{prices_all.loc[d, '华夏豆粕ETF']:.3f}"
            price_dict['博时可转债(511380.SH)'] = f"{prices_all.loc[d, '博时可转债ETF']:.3f}"
            price_dict['中欧纯债LOF(166016.SZ)'] = f"{prices_all.loc[d, '中欧纯债LOF']:.3f}"

        new_record = {
            'sig': current_sig, '开始日期': date_str, '结束日期': date_str, '交易天数': 1, '触发调仓逻辑': reason_str,
            '宽基(股)占比': f"{final_w_eq*100:.1f}%", '商品(商)占比': f"{final_w_com*100:.1f}%",
            '转债(债)占比': f"{final_w_cb*100:.1f}%", '纯债(水库)占比': f"{final_w_cdb*100:.1f}%"
        }
        new_record.update(price_dict)
        merged_records.append(new_record)
        last_state = new_record

final_records = [{k: v for k, v in r.items() if k != 'sig'} for r in merged_records]
df_merged_live = pd.DataFrame(final_records)

try:
    file_path_live = "实盘四核形态_本地版调仓日志.xlsx"
    df_merged_live.to_excel(file_path_live, index=False)
    print(f"\n✅ 成功导出！本地版审计账单已生成至：【{file_path_live}】")
except Exception as e: print(f"\n❌ 导出Excel失败: {e}")

print("\n========== 实盘调仓审计日志 (最近 10 次动作) ==========")
display_cols = ['开始日期', '交易天数', '触发调仓逻辑', '股端MA20触发价', '商端MA20触发价', '【股】合成价格', '【商】合成价格']
print(df_merged_live[display_cols].tail(10).to_string(index=False))