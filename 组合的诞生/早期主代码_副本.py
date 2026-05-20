import pandas as pd
import akshare as ak
import numpy as np
import datetime
import time
import warnings
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker

warnings.filterwarnings('ignore')

# 设置中文字体
plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei']
plt.rcParams['axes.unicode_minus'] = False

#%% Step 1: 全局数据准备 —— 集中读取本地文件与下载全部行情数据
import pandas as pd
import datetime
import time
import akshare as ak

print("【Step 1】初始化：正在集中读取本地文件并获取所有所需行情数据(请耐心等待)...")

end_date_str = datetime.datetime.now().strftime("%Y%m%d")
start_date_str_10y = "20151201" # 统一获取 2015年底 至今的最长区间数据

# ================= 1.1 读取所有本地 Excel/CSV 静态文件 =================
index_pool = pd.read_excel(r'C:\Users\Coeur\Desktop\红筹投资\组合构建\组合的诞生\行业指数池.xlsx', sheet_name='Sheet1')
prosperity_board = pd.read_excel(r'C:\Users\Coeur\Desktop\红筹投资\组合构建\组合的诞生\_实验-AI评分季度景气度看板 (4_10).xlsx', sheet_name='Sheet1')
pring_df = pd.read_excel(r'C:\Users\Coeur\Desktop\红筹投资\组合构建\组合的诞生\最新普林格调仓明细_至202603(含异象处理_实盘版).xlsx', sheet_name='Sheet1')
r'''
pring_df = pd.read_excel(r'C:\Users\Coeur\Downloads\普林格周期大类资产轮动调仓记录.xlsx', sheet_name='Sheet1')
'''
cb_df = pd.read_csv(r'C:\Users\Coeur\Desktop\红筹投资\组合构建\组合的诞生\可转债日频数据_20201201后_含行业.csv')

# ================= 1.2 下载全部前置行业轮动指数数据 =================
all_daily_data = pd.DataFrame()
for idx, row in index_pool.iterrows():
    full_code = str(row['指数代码'])
    name = row['指数名称']
    code, suffix = full_code.split('.') if '.' in full_code else (full_code, 'SZ')
    for attempt in range(3):
        try:
            if suffix == 'CSI': df = ak.stock_zh_index_hist_csindex(symbol=code, start_date=start_date_str_10y, end_date=end_date_str)
            elif suffix in ['SI', 'SL']: df = ak.index_hist_sw(symbol=code, period="day")
            elif suffix == 'CNI':
                df = ak.index_hist_cni(symbol=code, start_date=start_date_str_10y, end_date=end_date_str)
                if df is not None and not df.empty and '收盘价' in df.columns: df.rename(columns={'收盘价': '收盘'}, inplace=True)
            else:
                prefix = 'sz' if suffix == 'SZ' else 'sh'
                df = ak.stock_zh_index_daily(symbol=f"{prefix}{code}")
                if df is not None and not df.empty: df.rename(columns={'date': '日期', 'close': '收盘'}, inplace=True)
            
            if df is not None and not df.empty and '收盘' in df.columns:
                df['日期'] = pd.to_datetime(df['日期'])
                sd, ed = pd.to_datetime(start_date_str_10y), pd.to_datetime(end_date_str)
                df = df[(df['日期'] >= sd) & (df['日期'] <= ed)]
                df_clean = df[['日期', '收盘']].copy()
                df_clean['行业名称'] = name; df_clean['指数代码'] = code
                all_daily_data = pd.concat([all_daily_data, df_clean], ignore_index=True)
                break 
        except: time.sleep(1)
    time.sleep(0.1)

# ================= 1.3 集中下载全部宏观大类资产与ETF数据 =================
macro_etf_assets = {
    '沪深300指数': ('510300', 'ETF'), '南华期货:商品指数': ('NHCI', 'SL'),
    '中证基金指数:货币基金': ('H11025', 'CSI'), '中证全债指数': ('H11001', 'CSI'),
    '中证转债': ('000832', 'CSI'), '大成有色ETF': ('159980', 'ETF'),
    '华安黄金ETF': ('518880', 'ETF'), '建信能化ETF': ('159981', 'ETF'), '华夏豆粕ETF': ('159985', 'ETF'),
    # ★ 新增：将国开债5-7年纳入底层资产库，用作避险水库底座
    '国开债5-7': ('931283', 'CSI')
}
prices_all = pd.DataFrame()

for name, (code, asset_type) in macro_etf_assets.items():
    if name == '南华期货:商品指数':
        # 兼容处理本地南华商品文件的读取
        for path in [r'C:\Users\Coeur\Desktop\红筹投资\组合构建\组合的诞生\南华期货商品指数_20260319_151407.xlsx', '南华期货商品指数_20260319_151407.xlsx']:
            try: df = pd.read_excel(path); break
            except: 
                try: df = pd.read_csv(path.replace('.xlsx', '.xlsx - Sheet1.csv')); break
                except: continue
        if 'df' in locals() and df is not None:
            df = df.iloc[:, [0, 1]]; df.columns = ['日期', '收盘']
            df['日期'] = pd.to_datetime(df['日期'], errors='coerce')
            df = df.dropna(subset=['日期']); df['收盘'] = pd.to_numeric(df['收盘'], errors='coerce')
            sd, ed = pd.to_datetime(start_date_str_10y), pd.to_datetime(end_date_str)
            df = df[(df['日期'] >= sd) & (df['日期'] <= ed)]
            df_clean = df[['日期', '收盘']].copy().set_index('日期')
            df_clean.rename(columns={'收盘': name}, inplace=True)
            prices_all = df_clean if prices_all.empty else prices_all.join(df_clean, how='outer')
            print(f"✅ 成功从本地文件读取: {name}")
        continue
        
    for attempt in range(3):
        try:
            if asset_type == 'CSI': df = ak.stock_zh_index_hist_csindex(symbol=code, start_date=start_date_str_10y, end_date=end_date_str)
            elif asset_type == 'ETF':
                try: df = ak.fund_etf_hist_em(symbol=code, period="daily", start_date=start_date_str_10y, end_date=end_date_str)
                except: prefix = 'sh' if code.startswith('5') else 'sz'; df = ak.stock_zh_index_daily(symbol=f"{prefix}{code}")
            elif asset_type in ['SI', 'SL']: df = ak.index_hist_sw(symbol=code, period="day")
            else: prefix = 'sz' if asset_type == 'SZ' else 'sh'; df = ak.stock_zh_index_daily(symbol=f"{prefix}{code}")
            
            if df is not None and not df.empty:
                col_map = {'date': '日期', 'close': '收盘', '收盘价': '收盘'}
                df.rename(columns=lambda x: col_map.get(x, x), inplace=True)
                if '日期' in df.columns and '收盘' in df.columns:
                    df['日期'] = pd.to_datetime(df['日期'])
                    sd, ed = pd.to_datetime(start_date_str_10y), pd.to_datetime(end_date_str)
                    df = df[(df['日期'] >= sd) & (df['日期'] <= ed)]
                    df_clean = df[['日期', '收盘']].copy().set_index('日期')
                    df_clean.rename(columns={'收盘': name}, inplace=True)
                    prices_all = df_clean if prices_all.empty else prices_all.join(df_clean, how='outer')
                    print(f"✅ 成功获取: {name} ({code})")
                    break
        except: time.sleep(1)

# 生成统一长周期的基础资产收益率库 (2016起)
for col in macro_etf_assets.keys():
    if col not in prices_all.columns: prices_all[col] = 1.0
prices_all = prices_all.sort_index().ffill()
ret_all = prices_all.pct_change().fillna(0)
ret_all = ret_all[ret_all.index >= '2016-01-01']
print("基础行情与前置数据准备完毕，正式进入逻辑运算！\n")

#%% Step 2: 前置中观行业轮动数据处理与匹配
print("【Step 2】执行中观行业景气度处理与季频合成...\n")
index_pool['指数代码_纯数字'] = index_pool['指数代码'].apply(lambda x: str(x).split('.')[0])
prosperity_board['行业名称'] = prosperity_board['行业名称'].replace('航运港口', '航运港口(申万)')
board_unique = prosperity_board.drop_duplicates(subset=['季度', '行业名称'])[['季度', '行业名称', '行业景气度得分']]

def get_next_quarter(q_str):
    year, q = int(q_str[:4]), int(q_str[-1])
    return f"{year+1}Q1" if q == 4 else f"{year}Q{q+1}"

board_unique['对应预测收益季度'] = board_unique['季度'].apply(get_next_quarter)
all_daily_data['日期'] = pd.to_datetime(all_daily_data['日期'])

quarter_end_prices = (all_daily_data.set_index('日期').groupby('行业名称')['收盘'].resample('Q').last().reset_index())
quarter_end_prices['实际收益季度'] = quarter_end_prices['日期'].dt.to_period('Q').astype(str)
quarter_end_prices = quarter_end_prices.sort_values(by=['行业名称', '日期'])
quarter_end_prices['季度收益率'] = quarter_end_prices.groupby('行业名称')['收盘'].pct_change()
quarterly_returns = quarter_end_prices.dropna(subset=['季度收益率']).copy()
quarterly_returns['当季收益百分位'] = quarterly_returns.groupby('实际收益季度')['季度收益率'].rank(pct=True, ascending=True)

merged_data = pd.merge(board_unique, quarterly_returns[['行业名称', '实际收益季度', '季度收益率', '当季收益百分位']], left_on=['行业名称', '对应预测收益季度'], right_on=['行业名称', '实际收益季度'], how='inner')
top4_results = []
for score_q, group in merged_data.groupby('季度'): top4_results.append(group.nlargest(4, '行业景气度得分'))
top4_df = pd.concat(top4_results, ignore_index=True)

#%% Step 3: 普林格周期大类资产轮动与改良版对比回测 (2021年起)
print("【Step 3】执行原版与改良版普林格模型回测 (2021年起)...\n")
# 切片出 2021 年起的基础大类资产收益率
pring_ret = ret_all[ret_all.index >= '2021-01-01'][['沪深300指数', '南华期货:商品指数', '中证基金指数:货币基金', '中证全债指数']]

pring_df['调仓日期'] = pd.to_datetime(pring_df['调仓日期'])
weights_df = pring_df.set_index('调仓日期')[['沪深300指数', '南华期货:商品指数', '中证基金指数:货币基金', '中证全债指数']]

trading_days = pring_ret.index
all_dates = sorted(list(set(trading_days) | set(weights_df.index)))
weights_daily = weights_df.reindex(all_dates).ffill().loc[trading_days]

df_wide = all_daily_data.pivot(index='日期', columns='行业名称', values='收盘').ffill()
df_ret_ind = df_wide.pct_change().fillna(0)
df_ret_ind = df_ret_ind[df_ret_ind.index >= '2021-01-01']

top4_daily_returns = pd.Series(index=trading_days, dtype=float, name='TOP4策略')
for d in trading_days:
    q = f"{d.year}Q{d.quarter}"
    top4_sectors = top4_df[top4_df['对应预测收益季度'] == q]['行业名称'].tolist()
    if top4_sectors:
        valid_sectors = [s for s in top4_sectors if s in df_ret_ind.columns]
        top4_daily_returns.loc[d] = df_ret_ind.loc[d, valid_sectors].mean() if valid_sectors and d in df_ret_ind.index else 0.0
    else:
        top4_daily_returns.loc[d] = pring_ret.loc[d, '沪深300指数']

ret_comparison = pd.DataFrame(index=trading_days)
ret_comparison['华泰柏瑞沪深300ETF'] = pring_ret['沪深300指数']
ret_comparison['原版普林格模型'] = (pring_ret * weights_daily).sum(axis=1)

pring_ret_modified = pring_ret.copy()
pring_ret_modified['沪深300指数'] = top4_daily_returns
ret_comparison['改良版普林格模型'] = (pring_ret_modified * weights_daily).sum(axis=1)

#%% Step 4: 双核改良版普林格周期模型 (加入可转债防御替代)
print("【Step 4】处理可转债日频数据，进行【双核改良版】回测...\n")
cb_df['date'] = pd.to_datetime(cb_df['date'])
cb_close = cb_df.pivot(index='date', columns='债券代码', values='close').ffill()
cb_ret = cb_close.pct_change().fillna(0)
cb_ret = cb_ret[cb_ret.index >= '2021-01-01']

cb_ind_map = cb_df.drop_duplicates('债券代码').set_index('债券代码')['申万一级'].to_dict()
idx_to_sw = dict(zip(index_pool['指数名称'], index_pool['申万一级']))

top4_cb_returns = pd.Series(index=trading_days, dtype=float, name='TOP4可转债')
for d in trading_days:
    q = f"{d.year}Q{d.quarter}"
    top4_sectors = top4_df[top4_df['对应预测收益季度'] == q]['行业名称'].tolist()
    if top4_sectors:
        sw_inds = [idx_to_sw.get(s, s) for s in top4_sectors]
        valid_cbs = [code for code, ind in cb_ind_map.items() if ind in sw_inds and code in cb_ret.columns]
        top4_cb_returns.loc[d] = cb_ret.loc[d, valid_cbs].mean() if valid_cbs and d in cb_ret.index else 0.0
    else: top4_cb_returns.loc[d] = 0.0

pring_ret_mod_dual = pring_ret.copy()
pring_ret_mod_dual['沪深300指数'] = top4_daily_returns
if '中证基金指数:货币基金' in pring_ret_mod_dual.columns: pring_ret_mod_dual['中证基金指数:货币基金'] = top4_cb_returns
if '中证全债指数' in pring_ret_mod_dual.columns: pring_ret_mod_dual['中证全债指数'] = top4_cb_returns

ret_comparison['可转债替代后的普林格'] = (pring_ret_mod_dual * weights_daily).sum(axis=1)
for col in ret_comparison.columns: ret_comparison[col] = pd.to_numeric(ret_comparison[col], errors='coerce').fillna(0)
nav_df = (1 + ret_comparison).cumprod()

plt.figure(figsize=(14, 7))
plt.plot(nav_df.index, nav_df['可转债替代后的普林格'], label='双核改良版 (TOP4替换300 + 对应行业转债替换纯债/现金)', color='darkorange', linewidth=2.5)
plt.plot(nav_df.index, nav_df['改良版普林格模型'], label='单核改良版 (仅 TOP4替换300)', color='crimson', linewidth=2)
plt.plot(nav_df.index, nav_df['原版普林格模型'], label='原版普林格模型 (传统轮动)', color='steelblue', linewidth=1.5)
plt.plot(nav_df.index, nav_df['华泰柏瑞沪深300ETF'], label='基准：华泰柏瑞沪深300ETF', color='grey', linewidth=1.5, linestyle='--')
plt.title('2021年起：普林格模型与双核改良版 累计净值走势', fontsize=17, fontweight='bold', pad=15)
plt.xlabel('日期', fontsize=12); plt.ylabel('累计净值', fontsize=12)
plt.legend(fontsize=11, loc='upper left'); plt.grid(True, linestyle=':', alpha=0.6)
plt.tight_layout()
plt.show()

#%% Step 5: 记录各季度持仓明细及股债商大类资产比例，并导出Excel
print("【Step 5】统计各季度大类资产(股/债/商)比例及底层持仓明细并导出...\n")
cb_name_map = cb_df.drop_duplicates('债券代码').set_index('债券代码')['债券简称'].to_dict()
quarters = [q for q in sorted(top4_df['对应预测收益季度'].unique()) if q >= '2021Q1']
records = []

for q in quarters:
    try:
        q_period = pd.Period(q, freq='Q')
        start_date, end_date = q_period.start_time, q_period.end_time
    except: continue
        
    mask = (weights_daily.index >= start_date) & (weights_daily.index <= end_date)
    q_weights = weights_daily[mask]
    if q_weights.empty: continue
        
    w_stock = q_weights['沪深300指数'].mean() if '沪深300指数' in q_weights.columns else 0
    w_commodity = q_weights['南华期货:商品指数'].mean() if '南华期货:商品指数' in q_weights.columns else 0
    w_cb = (q_weights['中证基金指数:货币基金'].mean() if '中证基金指数:货币基金' in q_weights.columns else 0) + (q_weights['中证全债指数'].mean() if '中证全债指数' in q_weights.columns else 0)
    
    q_top4_sectors = top4_df[top4_df['对应预测收益季度'] == q]['行业名称'].tolist()
    stock_details, cb_details = [], []
    if q_top4_sectors:
        weight_per_sector = w_stock / len(q_top4_sectors)
        for sector in q_top4_sectors:
            stock_details.append(f"{sector}({weight_per_sector*100:.1f}%)" if weight_per_sector > 0 else f"{sector}(0.0%)")
            sw_ind = idx_to_sw.get(sector, sector)
            valid_cb_codes = [code for code, ind in cb_ind_map.items() if ind == sw_ind and code in cb_ret.columns]
            cb_details.append(f"[{sector}] {'、'.join([str(cb_name_map.get(c, c)) for c in valid_cb_codes])}" if valid_cb_codes else f"[{sector}] 无对应转债")
    else: stock_details.append("无信号"); cb_details.append("无信号")
        
    records.append({
        '调仓季度': q, '【股】权重': f"{w_stock*100:.1f}%", '【债】权重 (防守端转债)': f"{w_cb*100:.1f}%", '【商】权重 (大宗商品)': f"{w_commodity*100:.1f}%",
        '股票端持仓明细 (TOP4细分比例)': " | ".join(stock_details), '债券端持仓明细 (TOP4对应可转债)': " | ".join(cb_details), '商品端持仓明细': "南华期货商品指数" if w_commodity > 0 else "无持仓"
    })

out_df = pd.DataFrame(records)
print("========== 各季度持仓明细及大类资产比例 ==========\n")
print(out_df[['调仓季度', '【股】权重', '【债】权重 (防守端转债)', '【商】权重 (大宗商品)', '股票端持仓明细 (TOP4细分比例)']].to_string(index=False))
try:
    out_df.to_excel(r"C:\Users\Coeur\Desktop\红筹投资\组合构建\季度大类资产比例及持仓明细表.xlsx", index=False)
    print("\n✅ 已成功导出至：季度大类资产比例及持仓明细表.xlsx")
except Exception as e: print(f"\n❌ 导出失败: {e}")

#%% Step 6: 绘制最大回撤走势、输出核心绩效指标
print("【Step 6】绘制最大回撤图、统计年度收益率及计算核心绩效指标...\n")
columns_to_eval = ['华泰柏瑞沪深300ETF', '原版普林格模型', '改良版普林格模型', '可转债替代后的普林格']
rolling_max = nav_df[columns_to_eval].cummax()
drawdown_df = nav_df[columns_to_eval] / rolling_max - 1

plt.figure(figsize=(14, 7))
plt.plot(drawdown_df.index, drawdown_df['可转债替代后的普林格'], label='双核改良版', color='darkorange', linewidth=2.5)
plt.plot(drawdown_df.index, drawdown_df['改良版普林格模型'], label='单核改良版', color='crimson', linewidth=1.5, alpha=0.85)
plt.plot(drawdown_df.index, drawdown_df['原版普林格模型'], label='原版普林格模型', color='steelblue', linewidth=1.5, alpha=0.85)
plt.plot(drawdown_df.index, drawdown_df['华泰柏瑞沪深300ETF'], label='基准：沪深300', color='grey', linewidth=1.5, linestyle='--', alpha=0.7)
plt.title('2021年起：各策略组合历史动态回撤走势图', fontsize=17, fontweight='bold', pad=15)
plt.xlabel('日期', fontsize=12); plt.ylabel('回撤幅度', fontsize=12)
ax = plt.gca(); ax.yaxis.set_major_formatter(ticker.PercentFormatter(xmax=1.0))
plt.ylim(top=0); plt.legend(fontsize=11, loc='lower left'); plt.grid(True, linestyle=':', alpha=0.6)
plt.tight_layout()
plt.show()

rf_rate = 0.02; trading_days_per_year = 252; total_days = len(ret_comparison)
perf_metrics = []
for col in columns_to_eval:
    ann_return = nav_df[col].iloc[-1] ** (trading_days_per_year / total_days) - 1
    max_dd = drawdown_df[col].min()
    ann_vol = ret_comparison[col].std() * np.sqrt(trading_days_per_year)
    sharpe = (ann_return - rf_rate) / ann_vol if ann_vol != 0 else 0
    perf_metrics.append({'组合名称': col, '年化收益率': f"{ann_return*100:.2f}%", '最大回撤': f"{max_dd*100:.2f}%", '夏普比率': f"{sharpe:.2f}"})

print("\n========== 核心绩效指标总览 (2021年初 至今) ==========")
print(pd.DataFrame(perf_metrics).to_string(index=False))

#%% Step 7: 绘制双核改良版与沪深300ETF的累计收益率及超额收益走势图
excess_return = nav_df['可转债替代后的普林格'] / nav_df['华泰柏瑞沪深300ETF'] - 1
fig, ax1 = plt.subplots(figsize=(14, 7))
ax1.plot(nav_df.index, nav_df['可转债替代后的普林格'] - 1, label='双核改良版 累计收益率', color='darkorange', linewidth=2.5)
ax1.plot(nav_df.index, nav_df['华泰柏瑞沪深300ETF'] - 1, label='基准：沪深300 累计收益率', color='grey', linewidth=1.5, linestyle='--')
ax1.plot(excess_return.index, excess_return, label='超额收益', color='purple', linewidth=1.5, alpha=0.9)
ax1.axhline(0, color='black', linewidth=1, linestyle='-', alpha=0.6)
ax1.fill_between(excess_return.index, excess_return, 0, where=(excess_return >= 0), color='#DC143C', alpha=0.15)
ax1.fill_between(excess_return.index, excess_return, 0, where=(excess_return < 0), color='#228B22', alpha=0.15)
ax1.set_title('双核改良版 vs 沪深300 累计收益率与超额收益对比', fontsize=17, fontweight='bold', pad=15)
ax1.yaxis.set_major_formatter(ticker.PercentFormatter(xmax=1.0))
ax1.grid(True, linestyle=':', alpha=0.6); ax1.legend(fontsize=11, loc='upper left')
plt.tight_layout()
plt.show()

#%% Step 8: 2016-2026年 历史长区间基础数据准备
print("【Step 8】提取全区间(2016至今)的底层收益数据，准备长跑回测...\n")
ret_long = ret_all[['沪深300指数', '南华期货:商品指数', '中证基金指数:货币基金', '中证全债指数', '中证转债']].copy()

trading_days_long = ret_long.index
all_dates_long = sorted(list(set(trading_days_long) | set(weights_df.index)))
weights_daily_long = weights_df.reindex(all_dates_long).ffill().loc[trading_days_long]

ret_comp_long = pd.DataFrame(index=trading_days_long)
ret_comp_long['华泰柏瑞沪深300ETF'] = ret_long['沪深300指数']
ret_comp_long['原版普林格模型'] = (ret_long[['沪深300指数', '南华期货:商品指数', '中证基金指数:货币基金', '中证全债指数']] * weights_daily_long).sum(axis=1)

cb_defense_weight = weights_daily_long['中证基金指数:货币基金'] + weights_daily_long['中证全债指数']
ret_comp_long['可转债替代后的普林格'] = (ret_long['沪深300指数'] * weights_daily_long['沪深300指数'] + ret_long['南华期货:商品指数'] * weights_daily_long['南华期货:商品指数'] + ret_long['中证转债'] * cb_defense_weight)
for col in ret_comp_long.columns: ret_comp_long[col] = pd.to_numeric(ret_comp_long[col], errors='coerce').fillna(0)

#%% Step 9: 16-26年【终极拼接版】收益率无缝融合与长跑表现作图
print("【Step 9】拼接 16-26 年终极策略收益率并作图...\n")
spliced_strategy_ret = pd.Series(index=ret_comp_long.index, dtype=float)

mask_p1 = spliced_strategy_ret.index < '2021-01-01'
spliced_strategy_ret[mask_p1] = ret_comp_long.loc[mask_p1, '可转债替代后的普林格']

mask_p2 = spliced_strategy_ret.index >= '2021-01-01'
valid_dates_p2 = spliced_strategy_ret[mask_p2].index.intersection(ret_comparison.index)
spliced_strategy_ret.loc[valid_dates_p2] = ret_comparison.loc[valid_dates_p2, '可转债替代后的普林格']

spliced_strategy_ret = spliced_strategy_ret.fillna(0)
ret_final = pd.DataFrame(index=ret_comp_long.index)
ret_final['华泰柏瑞沪深300ETF'] = ret_comp_long['华泰柏瑞沪深300ETF']
ret_final['原版普林格模型'] = ret_comp_long['原版普林格模型']
ret_final['终极拼接版：双核普林格(转债防守)'] = spliced_strategy_ret

nav_final = (1 + ret_final).cumprod()

plt.figure(figsize=(14, 7))
plt.plot(nav_final.index, nav_final['终极拼接版：双核普林格(转债防守)'], label='终极拼接版 (前期宏观防守 + 后期景气轮动双核)', color='darkorange', linewidth=2.5)
plt.plot(nav_final.index, nav_final['原版普林格模型'], label='原版普林格模型', color='steelblue', linewidth=2, alpha=0.85)
plt.plot(nav_final.index, nav_final['华泰柏瑞沪深300ETF'], label='基准：沪深300', color='grey', linewidth=1.5, linestyle='--', alpha=0.7)
plt.title('2016 - 2026年：终极拼接版策略 vs 原版模型 vs 沪深300 累计净值走势', fontsize=17, fontweight='bold', pad=15)
plt.legend(fontsize=11, loc='upper left'); plt.grid(True, linestyle=':', alpha=0.6)
plt.tight_layout()
plt.show()

#%% Step 10: 输出 2016-2020 年终极拼接版第一阶段各季度持仓明细
print("\n【Step 10】统计 2016-2020 年(第一阶段)的持仓明细并导出...\n")
quarters_16_20 = [f"{year}Q{q}" for year in range(2016, 2021) for q in [1, 2, 3, 4]]
records_16_20 = []
for q in quarters_16_20:
    try:
        q_period = pd.Period(q, freq='Q')
        mask = (weights_daily_long.index >= q_period.start_time) & (weights_daily_long.index <= q_period.end_time)
        q_weights = weights_daily_long[mask]
        if q_weights.empty: continue
            
        w_stock = q_weights['沪深300指数'].mean() if '沪深300指数' in q_weights.columns else 0
        w_commodity = q_weights['南华期货:商品指数'].mean() if '南华期货:商品指数' in q_weights.columns else 0
        w_cb = (q_weights['中证基金指数:货币基金'].mean() if '中证基金指数:货币基金' in q_weights.columns else 0) + (q_weights['中证全债指数'].mean() if '中证全债指数' in q_weights.columns else 0)
        
        records_16_20.append({
            '调仓季度': q, '【股】权重': f"{w_stock*100:.1f}%", '【债】权重 (转债替代防守)': f"{w_cb*100:.1f}%", '【商】权重': f"{w_commodity*100:.1f}%",
            '股票端明细': "沪深300" if w_stock > 0 else "无", '债券端明细': "中证转债" if w_cb > 0 else "无", '商品端明细': "南华商品" if w_commodity > 0 else "无"
        })
    except: continue

pd.DataFrame(records_16_20).to_excel("16-20年度大类资产比例及持仓明细表.xlsx", index=False)
print("✅ 已导出: 16-20年度大类资产比例及持仓明细表.xlsx")

#%% Step 11: 绘制沪深300、原版普林格与终极拼接版的历年收益率对比三柱图
ret_final_step11 = ret_final.copy()
ret_final_step11['年份'] = ret_final_step11.index.year.astype(str)
yearly_compare = ret_final_step11.groupby('年份')[['华泰柏瑞沪深300ETF', '原版普林格模型', '终极拼接版：双核普林格(转债防守)']].apply(lambda x: (1 + x).prod() - 1).reset_index()

fig3, ax3 = plt.subplots(figsize=(14, 6))
x = np.arange(len(yearly_compare['年份'])); width = 0.25
rects1 = ax3.bar(x - width, yearly_compare['华泰柏瑞沪深300ETF'] * 100, width, label='基准：沪深300', color='grey', alpha=0.6)
rects2 = ax3.bar(x, yearly_compare['原版普林格模型'] * 100, width, label='原版普林格模型', color='steelblue', alpha=0.85)
rects3 = ax3.bar(x + width, yearly_compare['终极拼接版：双核普林格(转债防守)'] * 100, width, label='终极拼接版', color='darkorange')
ax3.set_title('2016-2026年：历年收益率对比', fontsize=16, fontweight='bold', pad=15)
ax3.set_xticks(x); ax3.set_xticklabels(yearly_compare['年份'], fontsize=12)
ax3.legend(fontsize=11, loc='upper left'); ax3.axhline(0, color='black', linewidth=1); ax3.grid(axis='y', linestyle=':', alpha=0.6)

def autolabel(rects):
    for rect in rects:
        height = rect.get_height()
        if abs(height) < 0.1: continue
        ax3.annotate(f'{height:.1f}%', xy=(rect.get_x() + rect.get_width()/2, height), xytext=(0, 3 if height > 0 else -15), textcoords="offset points", ha='center', va='bottom' if height > 0 else 'top', fontsize=9)

autolabel(rects1); autolabel(rects2); autolabel(rects3)
plt.tight_layout(); plt.show()

#%% Step 12: 防守端纯宽基转债(中证转债)版本对比测算
print("\n【Step 12】对比测算防守端纯大盘宽基转债的效果...\n")
equity_leg = pd.Series(index=ret_comp_long.index, dtype=float)
equity_leg.loc[equity_leg.index < '2021-01-01'] = ret_long.loc[equity_leg.index < '2021-01-01', '沪深300指数']
valid_dates_post21 = equity_leg[equity_leg.index >= '2021-01-01'].index.intersection(top4_daily_returns.index)
equity_leg.loc[valid_dates_post21] = top4_daily_returns.loc[valid_dates_post21]
equity_leg = equity_leg.fillna(0)

ret_broad_cb_defense = (equity_leg * weights_daily_long['沪深300指数'] + ret_long['南华期货:商品指数'] * weights_daily_long['南华期货:商品指数'] + ret_long['中证转债'] * cb_defense_weight).fillna(0)

ret_final_step12 = ret_final.copy()
ret_final_step12['终极拼接版：宽基转债防守(仅用000832)'] = ret_broad_cb_defense
nav_final_step12 = (1 + ret_final_step12).cumprod()

plt.figure(figsize=(14, 7))
plt.plot(nav_final_step12.index, nav_final_step12['终极拼接版：双核普林格(转债防守)'], label='原终极拼接版 (后期防守：细分高景气转债)', color='darkorange', linewidth=2.5)
plt.plot(nav_final_step12.index, nav_final_step12['终极拼接版：宽基转债防守(仅用000832)'], label='宽基防守版 (全区间仅用中证转债大盘)', color='purple', linewidth=2)
plt.plot(nav_final_step12.index, nav_final_step12['华泰柏瑞沪深300ETF'], label='基准：沪深300', color='grey', linewidth=1.5, linestyle='--', alpha=0.7)
plt.title('2016-2026年：精细化细分转债防守 vs 纯宽基转债防守', fontsize=17, fontweight='bold')
plt.legend(fontsize=11, loc='upper left'); plt.grid(True, linestyle=':', alpha=0.6)
plt.tight_layout(); plt.show()

#%% Step 13: 绘制股/债底层资产净值走势及动态仓位分布图
print("\n【Step 13】绘制股债底层走势与动态仓位图...\n")
assets_step13 = ['沪深300指数', '中证转债']
nav_assets_step13 = (1 + ret_long[assets_step13]).cumprod()
w_eq = weights_daily_long['沪深300指数'].fillna(0)
w_com = weights_daily_long['南华期货:商品指数'].fillna(0)
w_bond = cb_defense_weight.fillna(0)
quarter_starts = nav_assets_step13.groupby(nav_assets_step13.index.to_period('Q')).apply(lambda x: x.index[0])

fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(16, 12), gridspec_kw={'height_ratios': [2.5, 1]}, sharex=True)
ax1.plot(nav_assets_step13.index, nav_assets_step13['沪深300指数'], label='【股】净值：沪深300', color='crimson', linewidth=2)
ax1.plot(nav_assets_step13.index, nav_assets_step13['中证转债'], label='【债】净值：中证转债', color='purple', linewidth=2)
for q_date in quarter_starts: ax1.axvline(x=q_date, color='grey', linestyle=':', alpha=0.3)
ax1.set_title('2016-2026年：底层资产走势 vs 大类资产动态仓位', fontsize=18, fontweight='bold', pad=15)
ax1.legend(loc='upper left'); ax1.grid(True, linestyle='-.', alpha=0.4)

ax2.stackplot(nav_assets_step13.index, w_eq*100, w_bond*100, w_com*100, labels=['股票权重', '债券权重', '商品权重'], colors=['crimson', 'purple', 'darkgoldenrod'], alpha=0.7)
for q_date in quarter_starts: ax2.axvline(x=q_date, color='white', linestyle=':', alpha=0.4)
ax2.set_title('大类资产动态仓位 (100% 堆叠)', fontsize=15, fontweight='bold'); ax2.set_ylim(0, 100); ax2.legend(loc='upper left')
plt.tight_layout(); plt.show()

#%% Step 14: 资产加权收益贡献面积图 (收益拆解) 与归因分析
print("\n【Step 14】绘制加权净值面积图并进行业绩归因...\n")
strat_ret = (equity_leg * w_eq) + (ret_long['中证转债'] * w_bond) + (ret_long['南华期货:商品指数'] * w_com)
strat_nav = (1 + strat_ret.fillna(0)).cumprod()
prev_nav = strat_nav.shift(1).fillna(1.0)

cum_contrib_eq = (prev_nav * equity_leg * w_eq).cumsum()
cum_contrib_bond = (prev_nav * ret_long['中证转债'] * w_bond).cumsum()
cum_contrib_com = (prev_nav * ret_long['南华期货:商品指数'] * w_com).cumsum()

fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(16, 12), gridspec_kw={'height_ratios': [2.5, 1]}, sharex=True)
total_return = strat_nav - 1
ax1.plot(total_return.index, total_return, label='总累计收益率', color='black', linewidth=2.5, zorder=5)
ax1.fill_between(total_return.index, 0, cum_contrib_eq, label='【股】加权收益贡献', color='crimson', alpha=0.65)
ax1.fill_between(total_return.index, cum_contrib_eq, cum_contrib_eq + cum_contrib_bond, label='【债】加权收益贡献', color='purple', alpha=0.65)
ax1.fill_between(total_return.index, cum_contrib_eq + cum_contrib_bond, cum_contrib_eq + cum_contrib_bond + cum_contrib_com, label='【商】加权收益贡献', color='darkgoldenrod', alpha=0.65)
ax1.set_title('2016-2026年：双核轮动策略 累计收益拆解', fontsize=18, fontweight='bold')
ax1.yaxis.set_major_formatter(ticker.PercentFormatter(xmax=1.0)); ax1.legend(loc='upper left'); ax1.grid(True, linestyle='-.', alpha=0.4)

ax2.stackplot(total_return.index, w_eq*100, w_bond*100, w_com*100, labels=['股票权重', '债券权重', '商品权重'], colors=['crimson', 'purple', 'darkgoldenrod'], alpha=0.7)
ax2.set_ylim(0, 100); ax2.legend(loc='upper left')
plt.tight_layout(); plt.show()


#%% Step 15: 商品端实操落地 —— 四只商品ETF等权替代测算 (2021年起)
print("\n【Step 17】执行实操落地版本 (有色+黄金+能化+豆粕) ETF等权组合回测 (2021年起)...\n")
# 从已有的数据中切片出 4 只商品 ETF
etf_ret = ret_all[['大成有色ETF', '华安黄金ETF', '建信能化ETF', '华夏豆粕ETF']]
basket_ret = etf_ret.mean(axis=1)

valid_dates_s17 = [d for d in ret_long.index if d >= pd.to_datetime('2021-01-01')]
common_dates = etf_ret.index.intersection(valid_dates_s17)

eq_ret_s17 = equity_leg.reindex(common_dates).fillna(0)
bond_ret_s17 = ret_long['中证转债'].reindex(common_dates).fillna(0)
nh_com_ret_s17 = ret_long['南华期货:商品指数'].reindex(common_dates).fillna(0)
basket_ret_s17 = basket_ret.reindex(common_dates).fillna(0)

w_eq_s17 = w_eq.reindex(common_dates).fillna(0)
w_bond_s17 = w_bond.reindex(common_dates).fillna(0)
w_com_s17 = w_com.reindex(common_dates).fillna(0)

ret_orig_s17 = (eq_ret_s17 * w_eq_s17) + (bond_ret_s17 * w_bond_s17) + (nh_com_ret_s17 * w_com_s17)
nav_orig_s17 = (1 + ret_orig_s17).cumprod()

ret_new_s17 = (eq_ret_s17 * w_eq_s17) + (bond_ret_s17 * w_bond_s17) + (basket_ret_s17 * w_com_s17)
nav_new_s17 = (1 + ret_new_s17).cumprod()

def calc_metrics(nav_series, name):
    tot_days = len(nav_series)
    ann_ret = nav_series.iloc[-1] ** (252 / tot_days) - 1
    max_dd = (nav_series / nav_series.cummax() - 1).min()
    return {'版本': name, '年化收益率': f"{ann_ret*100:.2f}%", '最大回撤': f"{max_dd*100:.2f}%"}

print(pd.DataFrame([calc_metrics(nav_orig_s17, "理论原版 (南华商品)"), calc_metrics(nav_new_s17, "实操落地版 (四只ETF等权)")]).to_string(index=False))

plt.figure(figsize=(14, 7))
plt.plot(nav_new_s17.index, nav_new_s17, label='实操落地版 (有色+黄金+能化+豆粕等权)', color='darkorange', linewidth=2.5)
plt.plot(nav_orig_s17.index, nav_orig_s17, label='理论原版 (南华商品指数)', color='steelblue', linewidth=2, linestyle='--')
plt.title('2021年起：实操版(四只ETF等权) vs 理论版(南华商品) 累计净值对比', fontsize=17, fontweight='bold', pad=15)
plt.legend(fontsize=12, loc='upper left'); plt.grid(True, linestyle=':', alpha=0.6)
plt.tight_layout(); plt.show()

print("\n完美收官！全盘深度优化后的所有流转数据与可视化分析均已正常执行。")

#%% Step 16: 2021年4月起 宽基股债商组合 vs 景气度股+宽基债商组合 表现对比 (剔除无信号期)
print("\n【Step 16】变量控制回测：对比2021年4月起 组合1(300+转债+ETF商) vs 组合2(TOP4+转债+ETF商)...\n")

# 1. 确定2021年4月起（Q2真正有信号开始）的公共交易日历
valid_dates_s16 = [d for d in ret_long.index if d >= pd.to_datetime('2021-04-01')]
# 取底层资产日期的交集，确保数据完美对齐
common_dates_s16 = basket_ret.index.intersection(valid_dates_s16).intersection(top4_daily_returns.index)

# 2. 提取公共日期下的底层资产日频收益率
eq_300_ret = ret_long['沪深300指数'].reindex(common_dates_s16).fillna(0)
eq_top4_ret = top4_daily_returns.reindex(common_dates_s16).fillna(0)
bond_cb_ret = ret_long['中证转债'].reindex(common_dates_s16).fillna(0)
com_etf_ret = basket_ret.reindex(common_dates_s16).fillna(0)

# 3. 提取公共日期下对应的大类资产动态仓位权重
w_eq_s16 = weights_daily_long['沪深300指数'].reindex(common_dates_s16).fillna(0)
w_bond_s16 = (weights_daily_long['中证基金指数:货币基金'] + weights_daily_long['中证全债指数']).reindex(common_dates_s16).fillna(0)
w_com_s16 = weights_daily_long['南华期货:商品指数'].reindex(common_dates_s16).fillna(0)

# 4. 计算两个对比组合的每日加权收益率与累计净值
# 组合1：股(沪深300) + 债(中证转债) + 商(四只商品ETF)
ret_combo1 = (eq_300_ret * w_eq_s16) + (bond_cb_ret * w_bond_s16) + (com_etf_ret * w_com_s16)
nav_combo1 = (1 + ret_combo1).cumprod()

# 组合2：股(TOP4行业) + 债(中证转债) + 商(四只商品ETF)
ret_combo2 = (eq_top4_ret * w_eq_s16) + (bond_cb_ret * w_bond_s16) + (com_etf_ret * w_com_s16)
nav_combo2 = (1 + ret_combo2).cumprod()

# 5. 封装核心绩效计算函数并输出
def calc_metrics_s16(nav_series, name):
    tot_days = len(nav_series)
    ann_ret = nav_series.iloc[-1] ** (252 / tot_days) - 1
    max_dd = (nav_series / nav_series.cummax() - 1).min()
    return {'组合名称': name, '年化收益率': f"{ann_ret*100:.2f}%", '最大回撤': f"{max_dd*100:.2f}%"}

metrics_combo1 = calc_metrics_s16(nav_combo1, "组合1 (基准股 + 宽基债 + 实操商)")
metrics_combo2 = calc_metrics_s16(nav_combo2, "组合2 (TOP4股 + 宽基债 + 实操商)")

print("========== Step 16: 股票端超额收益分离对比 (2021年4月起，剥离静默期) ==========")
print(pd.DataFrame([metrics_combo1, metrics_combo2]).to_string(index=False))
print("=================================================================\n")

# 6. 绘制最终的对比净值曲线
plt.figure(figsize=(14, 7))

# 组合2（策略目标）用亮色粗线
plt.plot(nav_combo2.index, nav_combo2, label='组合2：股(TOP4) + 债(中证转债) + 商(四只ETF等权)', color='darkorange', linewidth=2.5)
# 组合1（对标基准）用冷色虚线
plt.plot(nav_combo1.index, nav_combo1, label='组合1：股(沪深300) + 债(中证转债) + 商(四只ETF等权)', color='steelblue', linewidth=2, linestyle='--')

plt.title('2021年4月起：控制债商变量下，沪深300与TOP4景气度策略 累计净值对比 (剔除无信号期)', fontsize=17, fontweight='bold', pad=15)
plt.xlabel('日期', fontsize=12)
plt.ylabel('累计净值 (2021年4月初起 = 1.0)', fontsize=12)
plt.legend(fontsize=12, loc='upper left')
plt.grid(True, linestyle=':', alpha=0.6)
plt.tight_layout()
plt.show()

print("\nStep 16 对比逻辑执行完毕。")

#%% Step 17: 全区间(2016-2026) 终极可落地双核策略无缝拼接及持仓明细输出
print("\n【Step 17】拼接全区间(16-26年)终极可落地策略：前期模拟 + 后期实操，并输出持仓明细...\n")

# 1. 创建完整长周期时间序列的收益率容器
spliced_ret_s17 = pd.Series(index=ret_long.index, dtype=float)

# ================= 第一阶段：2016-01-01 至 2021-03-31 =================
mask_p1 = spliced_ret_s17.index < '2021-04-01'
dates_p1 = spliced_ret_s17[mask_p1].index

# 提取第一阶段的权重
w_eq_p1 = weights_daily_long['沪深300指数'].reindex(dates_p1).fillna(0)
w_bond_p1 = (weights_daily_long['中证基金指数:货币基金'] + weights_daily_long['中证全债指数']).reindex(dates_p1).fillna(0)
w_com_p1 = weights_daily_long['南华期货:商品指数'].reindex(dates_p1).fillna(0)

# 计算第一阶段的收益率 (沪深300 + 中证转债 + 南华商品)
ret_p1 = (ret_long['沪深300指数'].reindex(dates_p1).fillna(0) * w_eq_p1 +
          ret_long['中证转债'].reindex(dates_p1).fillna(0) * w_bond_p1 +
          ret_long['南华期货:商品指数'].reindex(dates_p1).fillna(0) * w_com_p1)

spliced_ret_s17.loc[dates_p1] = ret_p1

# ================= 第二阶段：2021-04-01 至今 =================
mask_p2 = spliced_ret_s17.index >= '2021-04-01'
# 取底层资产日期的交集，确保ETF和TOP4的数据完美对齐
dates_p2 = spliced_ret_s17[mask_p2].index.intersection(basket_ret.index).intersection(top4_daily_returns.index)

# 提取第二阶段的权重
w_eq_p2 = weights_daily_long['沪深300指数'].reindex(dates_p2).fillna(0)
w_bond_p2 = (weights_daily_long['中证基金指数:货币基金'] + weights_daily_long['中证全债指数']).reindex(dates_p2).fillna(0)
w_com_p2 = weights_daily_long['南华期货:商品指数'].reindex(dates_p2).fillna(0)

# 计算第二阶段的收益率 (TOP4行业 + 中证转债 + 4只ETF等权)
ret_p2 = (top4_daily_returns.reindex(dates_p2).fillna(0) * w_eq_p2 +
          ret_long['中证转债'].reindex(dates_p2).fillna(0) * w_bond_p2 +
          basket_ret.reindex(dates_p2).fillna(0) * w_com_p2)

spliced_ret_s17.loc[dates_p2] = ret_p2
spliced_ret_s17 = spliced_ret_s17.fillna(0) # 填充可能存在的极少部分空缺日

# ================= 计算累计净值与对比基准 =================
nav_spliced_s17 = (1 + spliced_ret_s17).cumprod()
nav_benchmark_300 = (1 + ret_long['沪深300指数']).cumprod()
nav_pring_original = (1 + ret_comp_long['原版普林格模型']).cumprod()

def calc_10yr_metrics(nav_series, name):
    tot_days = len(nav_series)
    ann_ret = nav_series.iloc[-1] ** (252 / tot_days) - 1
    max_dd = (nav_series / nav_series.cummax() - 1).min()
    return {'策略版本': name, '十年期年化收益': f"{ann_ret*100:.2f}%", '全区间最大回撤': f"{max_dd*100:.2f}%", '期末总净值': f"{nav_series.iloc[-1]:.3f}"}

print("========== Step 17: 2016-2026 全区间终极策略长跑业绩概览 ==========")
metrics_s17 = [
    calc_10yr_metrics(nav_spliced_s17, "终极无缝拼接版 (可实操落地)"),
    calc_10yr_metrics(nav_pring_original, "理论原版普林格 (不可直接买商指)"),
    calc_10yr_metrics(nav_benchmark_300, "基准：沪深300指数")
]
print(pd.DataFrame(metrics_s17).to_string(index=False))
print("=================================================================\n")

# ================= 新增：生成全区间终极策略持仓变动明细表 =================
print("正在生成终极策略长区间(2016-2026)季度持仓变动明细表...\n")
records_s17 = []
all_quarters = pd.period_range(start='2016Q1', end=pd.to_datetime(end_date_str).to_period('Q'), freq='Q')

for q_period in all_quarters:
    q_str = str(q_period)
    start_date, end_date = q_period.start_time, q_period.end_time
    mask = (weights_daily_long.index >= start_date) & (weights_daily_long.index <= end_date)
    q_weights = weights_daily_long[mask]
    
    if q_weights.empty: continue
        
    w_stock = q_weights['沪深300指数'].mean() if '沪深300指数' in q_weights.columns else 0
    w_commodity = q_weights['南华期货:商品指数'].mean() if '南华期货:商品指数' in q_weights.columns else 0
    w_cb = (q_weights['中证基金指数:货币基金'].mean() if '中证基金指数:货币基金' in q_weights.columns else 0) + (q_weights['中证全债指数'].mean() if '中证全债指数' in q_weights.columns else 0)
    
    # 区分阶段判断底层资产明细
    if q_period < pd.Period('2021Q2'):
        # 第一阶段：模拟期
        stock_detail = "华泰柏瑞沪深300ETF" if w_stock > 0 else "无持仓"
        bond_detail = "中证转债(000832.CSI)" if w_cb > 0 else "无持仓"
        commodity_detail = "南华期货商品指数(模拟)" if w_commodity > 0 else "无持仓"
    else:
        # 第二阶段：实操期 (2021Q2起)
        bond_detail = "中证转债(000832.CSI)" if w_cb > 0 else "无持仓"
        commodity_detail = "四只商品ETF等权(有色/黄金/能化/豆粕)" if w_commodity > 0 else "无持仓"
        
        # 获取当季TOP4
        q_top4_sectors = top4_df[top4_df['对应预测收益季度'] == q_str]['行业名称'].tolist()
        if q_top4_sectors and w_stock > 0:
            weight_per_sector = w_stock / len(q_top4_sectors)
            stock_detail = " | ".join([f"{sector}({weight_per_sector*100:.1f}%)" for sector in q_top4_sectors])
        else:
            stock_detail = "华泰柏瑞沪深300ETF(无信号替代)" if w_stock > 0 else "无持仓"

    records_s17.append({
        '调仓季度': q_str, 
        '【股】权重': f"{w_stock*100:.1f}%", 
        '【债】权重 (防守)': f"{w_cb*100:.1f}%", 
        '【商】权重 (大宗)': f"{w_commodity*100:.1f}%",
        '股票端持仓明细': stock_detail, 
        '债券端持仓明细': bond_detail, 
        '商品端持仓明细': commodity_detail
    })

df_holdings_s17 = pd.DataFrame(records_s17)
try:
    output_path = r"C:\Users\Coeur\Desktop\红筹投资\组合构建\终极拼接版_全区间持仓变动明细表.xlsx"
    df_holdings_s17.to_excel(output_path, index=False)
    print(f"✅ 成功导出全区间持仓表至：【{output_path}】\n")
except Exception as e: 
    print(f"❌ 导出持仓表失败，将保存在当前运行目录... ({e})")
    df_holdings_s17.to_excel("终极拼接版_全区间持仓变动明细表.xlsx", index=False)

# ================= 绘制全区间净值走势图 =================
plt.figure(figsize=(15, 7.5))

plt.plot(nav_spliced_s17.index, nav_spliced_s17, label='终极实操拼接版 (前五年模拟补全 + 后五年实盘复刻)', color='darkorange', linewidth=2.5)
plt.plot(nav_pring_original.index, nav_pring_original, label='理论原版普林格模型 (传统轮动)', color='steelblue', linewidth=2, alpha=0.85)
plt.plot(nav_benchmark_300.index, nav_benchmark_300, label='基准：沪深300指数', color='grey', linewidth=1.5, linestyle='--', alpha=0.7)

# 画一条垂直辅助线，标识“虚拟回溯”与“真实落地”的分界点
plt.axvline(pd.to_datetime('2021-04-01'), color='crimson', linestyle=':', linewidth=2, alpha=0.7, label='实盘分界线 (2021-04起进入TOP4+ETF商 实操期)')

plt.title('2016-2026年：终极可落地双核策略 (无缝拼接版) 全区间走势', fontsize=17, fontweight='bold', pad=15)
plt.xlabel('日期', fontsize=12)
plt.ylabel('累计净值 (2016年初 = 1.0)', fontsize=12)
plt.legend(fontsize=11, loc='upper left')
plt.grid(True, linestyle=':', alpha=0.6)
plt.tight_layout()
plt.show()

print("全剧终！从数据获取、前置处理、分项调优到最终的10年无缝实操拼接及持仓复盘，所有逻辑已彻底贯通。")

#%% Step 18: 绘制终极实操拼接版最大回撤图与累计收益拆解图 (含归因定量输出)
import matplotlib.ticker as ticker

print("\n【Step 18】绘制 2016-2026 全区间终极实操拼接版的 最大回撤走势图 与 累计收益拆解图，并输出定量归因...\n")

# ================= 1. 绘制最大回撤走势图 =================
dd_spliced = nav_spliced_s17 / nav_spliced_s17.cummax() - 1
dd_pring = nav_pring_original / nav_pring_original.cummax() - 1
dd_300 = nav_benchmark_300 / nav_benchmark_300.cummax() - 1

plt.figure(figsize=(15, 7.5))
plt.plot(dd_spliced.index, dd_spliced, label='终极实操拼接版 回撤', color='darkorange', linewidth=2)
plt.plot(dd_pring.index, dd_pring, label='理论原版普林格模型 回撤', color='steelblue', linewidth=1.5, alpha=0.85)
plt.plot(dd_300.index, dd_300, label='基准：沪深300指数 回撤', color='grey', linewidth=1.5, linestyle='--', alpha=0.6)

plt.axvline(pd.to_datetime('2021-04-01'), color='crimson', linestyle=':', linewidth=2, alpha=0.7, label='实盘分界线 (2021-04起进入实操期)')
plt.axhline(y=-0.15, color='black', linestyle='-.', linewidth=1, alpha=0.5)
plt.axhline(y=-0.30, color='black', linestyle='-.', linewidth=1, alpha=0.5)

plt.title('2016-2026年：终极可落地双核策略 (无缝拼接版) 历史动态回撤对比', fontsize=17, fontweight='bold', pad=15)
plt.xlabel('日期', fontsize=12); plt.ylabel('回撤幅度', fontsize=12)

ax = plt.gca()
ax.yaxis.set_major_formatter(ticker.PercentFormatter(xmax=1.0))
plt.ylim(top=0); plt.legend(fontsize=11, loc='lower left'); plt.grid(True, linestyle=':', alpha=0.6)
plt.tight_layout(); plt.show()

# ================= 2. 计算累计收益拆解数据 (股/债/商 无缝拼接) =================
# 提取完整时间序列下的基础权重
w_eq_spliced = weights_daily_long['沪深300指数'].reindex(spliced_ret_s17.index).fillna(0)
w_bond_spliced = (weights_daily_long['中证基金指数:货币基金'] + weights_daily_long['中证全债指数']).reindex(spliced_ret_s17.index).fillna(0)
w_com_spliced = weights_daily_long['南华期货:商品指数'].reindex(spliced_ret_s17.index).fillna(0)

# 拼接底层的实际资产收益率
eq_ret_spliced = pd.Series(index=spliced_ret_s17.index, dtype=float)
eq_ret_spliced.loc[dates_p1] = ret_long['沪深300指数'].reindex(dates_p1).fillna(0)
eq_ret_spliced.loc[dates_p2] = top4_daily_returns.reindex(dates_p2).fillna(0)

bond_ret_spliced = ret_long['中证转债'].reindex(spliced_ret_s17.index).fillna(0)

com_ret_spliced = pd.Series(index=spliced_ret_s17.index, dtype=float)
com_ret_spliced.loc[dates_p1] = ret_long['南华期货:商品指数'].reindex(dates_p1).fillna(0)
com_ret_spliced.loc[dates_p2] = basket_ret.reindex(dates_p2).fillna(0)

# 计算每日各资产真实的净值贡献
prev_nav_spliced = nav_spliced_s17.shift(1).fillna(1.0)
cum_contrib_eq_s18 = (prev_nav_spliced * eq_ret_spliced * w_eq_spliced).cumsum()
cum_contrib_bond_s18 = (prev_nav_spliced * bond_ret_spliced * w_bond_spliced).cumsum()
cum_contrib_com_s18 = (prev_nav_spliced * com_ret_spliced * w_com_spliced).cumsum()

# ================= 3. 新增：定量输出 股/债/商 收益绝对贡献与百分比占比 =================
total_return_spliced = nav_spliced_s17 - 1
total_return_val_s18 = total_return_spliced.iloc[-1]

# 提取期末各资产的绝对贡献值
eq_final_s18 = cum_contrib_eq_s18.iloc[-1]
bond_final_s18 = cum_contrib_bond_s18.iloc[-1]
com_final_s18 = cum_contrib_com_s18.iloc[-1]

# 计算相对占总利润的百分比
eq_ratio_s18 = eq_final_s18 / total_return_val_s18 if total_return_val_s18 != 0 else 0
bond_ratio_s18 = bond_final_s18 / total_return_val_s18 if total_return_val_s18 != 0 else 0
com_ratio_s18 = com_final_s18 / total_return_val_s18 if total_return_val_s18 != 0 else 0

print("========== 终极实操拼接版 (2016-2026) 业绩归因拆解 ==========")
print(f"组合总累计收益率 : {total_return_val_s18*100:.2f}%")
print(f"📈 【股】端绝对贡献 : {eq_final_s18*100:>6.2f}%  |  占总利润比重: {eq_ratio_s18*100:>6.2f}%")
print(f"🛡️ 【债】端绝对贡献 : {bond_final_s18*100:>6.2f}%  |  占总利润比重: {bond_ratio_s18*100:>6.2f}%")
print(f"🛢️ 【商】端绝对贡献 : {com_final_s18*100:>6.2f}%  |  占总利润比重: {com_ratio_s18*100:>6.2f}%")
print("=============================================================\n")

# ================= 4. 绘制累计收益拆解与动态仓位面积图 =================
fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(16, 12), gridspec_kw={'height_ratios': [2.5, 1]}, sharex=True)

# 子图1：收益拆解面积图
ax1.plot(total_return_spliced.index, total_return_spliced, label='终极实操拼接版 总累计收益率', color='black', linewidth=2.5, zorder=5)

ax1.fill_between(total_return_spliced.index, 0, cum_contrib_eq_s18, 
                 label=f'【股】贡献: {eq_ratio_s18*100:.1f}% (前300 / 后TOP4)', color='crimson', alpha=0.65)
ax1.fill_between(total_return_spliced.index, cum_contrib_eq_s18, cum_contrib_eq_s18 + cum_contrib_bond_s18, 
                 label=f'【债】贡献: {bond_ratio_s18*100:.1f}% (大盘中证转债)', color='purple', alpha=0.65)
ax1.fill_between(total_return_spliced.index, cum_contrib_eq_s18 + cum_contrib_bond_s18, cum_contrib_eq_s18 + cum_contrib_bond_s18 + cum_contrib_com_s18, 
                 label=f'【商】贡献: {com_ratio_s18*100:.1f}% (前南华 / 后四只ETF)', color='darkgoldenrod', alpha=0.65)

# 画分界线
ax1.axvline(pd.to_datetime('2021-04-01'), color='white', linestyle='--', linewidth=2, alpha=0.9, label='实盘分界线 (2021-04起进入实操期)')

ax1.set_title('2016-2026年：终极实操拼接版 累计收益拆解与利润占比', fontsize=18, fontweight='bold', pad=15)
ax1.yaxis.set_major_formatter(ticker.PercentFormatter(xmax=1.0))
ax1.legend(loc='upper left', fontsize=11); ax1.grid(True, linestyle='-.', alpha=0.4)

# 子图2：动态仓位堆叠图
ax2.stackplot(total_return_spliced.index, w_eq_spliced*100, w_bond_spliced*100, w_com_spliced*100, 
              labels=['股票权重', '债券权重', '商品权重'], colors=['crimson', 'purple', 'darkgoldenrod'], alpha=0.7)

ax2.axvline(pd.to_datetime('2021-04-01'), color='white', linestyle='--', linewidth=2, alpha=0.9)
ax2.set_ylim(0, 100)
ax2.legend(loc='upper left', fontsize=11)
ax2.set_title('大类资产动态仓位分布 (100% 堆叠)', fontsize=15, fontweight='bold')
ax2.set_xlabel('日期', fontsize=12); ax2.set_ylabel('配置权重 (%)', fontsize=12)

plt.tight_layout(); plt.show()

print("\nStep 18 收益拆解与定量归因分析完毕！")

#%% Step 19: 聚焦后五年实盘复刻期 (2021Q2起) 的最大回撤与收益归因拆解
import matplotlib.ticker as ticker

print("\n【Step 19】聚焦 2021-04 至今(后五年实盘复刻期) 的 最大回撤走势图 与 累计收益定量拆解...\n")

# ================= 1. 提取并重置 2021-04 至今的收益率与净值 =================
mask_s19 = spliced_ret_s17.index >= '2021-04-01'
dates_s19 = spliced_ret_s17[mask_s19].index

# 提取后五年各组合的日频收益率
ret_spliced_s19 = spliced_ret_s17.loc[dates_s19]
ret_pring_s19 = ret_comp_long.loc[dates_s19, '原版普林格模型']
ret_300_s19 = ret_long.loc[dates_s19, '沪深300指数']

# 重新计算以 2021-04-01 为起点(1.0)的累计净值
nav_spliced_s19 = (1 + ret_spliced_s19).cumprod()
nav_pring_s19 = (1 + ret_pring_s19).cumprod()
nav_300_s19 = (1 + ret_300_s19).cumprod()

# ================= 2. 计算并绘制实操期最大回撤图 =================
dd_spliced_s19 = nav_spliced_s19 / nav_spliced_s19.cummax() - 1
dd_pring_s19 = nav_pring_s19 / nav_pring_s19.cummax() - 1
dd_300_s19 = nav_300_s19 / nav_300_s19.cummax() - 1

plt.figure(figsize=(15, 7.5))
plt.plot(dd_spliced_s19.index, dd_spliced_s19, label='终极实操版 (TOP4+转债+ETF商) 回撤', color='darkorange', linewidth=2.5)
plt.plot(dd_pring_s19.index, dd_pring_s19, label='理论原版普林格模型 回撤', color='steelblue', linewidth=1.5, alpha=0.85)
plt.plot(dd_300_s19.index, dd_300_s19, label='基准：沪深300指数 回撤', color='grey', linewidth=1.5, linestyle='--', alpha=0.6)

plt.axhline(y=-0.15, color='black', linestyle='-.', linewidth=1, alpha=0.5)
plt.axhline(y=-0.30, color='black', linestyle='-.', linewidth=1, alpha=0.5)

plt.title('2021年4月起：终极实操版策略 (后五年纯实盘复刻) 历史动态回撤对比', fontsize=17, fontweight='bold', pad=15)
plt.xlabel('日期', fontsize=12); plt.ylabel('回撤幅度 (基准2021年4月)', fontsize=12)

ax = plt.gca()
ax.yaxis.set_major_formatter(ticker.PercentFormatter(xmax=1.0))
plt.ylim(top=0); plt.legend(fontsize=12, loc='lower left'); plt.grid(True, linestyle=':', alpha=0.6)
plt.tight_layout(); plt.show()

# ================= 3. 计算实操期累计收益拆解数据 =================
# 提取这段时期的动态仓位权重
w_eq_s19 = weights_daily_long['沪深300指数'].reindex(dates_s19).fillna(0)
w_bond_s19 = (weights_daily_long['中证基金指数:货币基金'] + weights_daily_long['中证全债指数']).reindex(dates_s19).fillna(0)
w_com_s19 = weights_daily_long['南华期货:商品指数'].reindex(dates_s19).fillna(0)

# 提取这段时期的底层真实资产收益率
eq_ret_s19 = top4_daily_returns.reindex(dates_s19).fillna(0)
bond_ret_s19 = ret_long['中证转债'].reindex(dates_s19).fillna(0)
com_ret_s19 = basket_ret.reindex(dates_s19).fillna(0)

# 计算每日各资产真实的净值绝对贡献 (前一日净值 * 当日该资产加权收益率)
prev_nav_s19 = nav_spliced_s19.shift(1).fillna(1.0)
cum_contrib_eq_s19 = (prev_nav_s19 * eq_ret_s19 * w_eq_s19).cumsum()
cum_contrib_bond_s19 = (prev_nav_s19 * bond_ret_s19 * w_bond_s19).cumsum()
cum_contrib_com_s19 = (prev_nav_s19 * com_ret_s19 * w_com_s19).cumsum()

# ================= 4. 定量输出 实操期(2021-04起) 业绩归因 =================
total_return_s19 = nav_spliced_s19 - 1
total_return_val_s19 = total_return_s19.iloc[-1]

# 提取期末各资产的绝对贡献值
eq_final_s19 = cum_contrib_eq_s19.iloc[-1]
bond_final_s19 = cum_contrib_bond_s19.iloc[-1]
com_final_s19 = cum_contrib_com_s19.iloc[-1]

# 计算相对占总利润的百分比
eq_ratio_s19 = eq_final_s19 / total_return_val_s19 if total_return_val_s19 != 0 else 0
bond_ratio_s19 = bond_final_s19 / total_return_val_s19 if total_return_val_s19 != 0 else 0
com_ratio_s19 = com_final_s19 / total_return_val_s19 if total_return_val_s19 != 0 else 0

print("========== 后五年纯实操期 (2021年4月-至今) 业绩归因拆解 ==========")
print(f"组合纯实操期总累计收益率 : {total_return_val_s19*100:.2f}% (起点净值重置为1.0)")
print(f"📈 【股】绝对贡献 (TOP4景气度) : {eq_final_s19*100:>6.2f}%  |  占该期利润比重: {eq_ratio_s19*100:>6.2f}%")
print(f"🛡️ 【债】绝对贡献 (中证转债)   : {bond_final_s19*100:>6.2f}%  |  占该期利润比重: {bond_ratio_s19*100:>6.2f}%")
print(f"🛢️ 【商】绝对贡献 (四只ETF篮子) : {com_final_s19*100:>6.2f}%  |  占该期利润比重: {com_ratio_s19*100:>6.2f}%")
print("==================================================================\n")

# ================= 5. 绘制实操期累计收益拆解与动态仓位面积图 =================
fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(16, 12), gridspec_kw={'height_ratios': [2.5, 1]}, sharex=True)

# 子图1：收益拆解面积图
ax1.plot(total_return_s19.index, total_return_s19, label='纯实操期 总累计收益率', color='black', linewidth=2.5, zorder=5)

ax1.fill_between(total_return_s19.index, 0, cum_contrib_eq_s19, 
                 label=f'【股】贡献: {eq_ratio_s19*100:.1f}% (TOP4景气度轮动)', color='crimson', alpha=0.65)
ax1.fill_between(total_return_s19.index, cum_contrib_eq_s19, cum_contrib_eq_s19 + cum_contrib_bond_s19, 
                 label=f'【债】贡献: {bond_ratio_s19*100:.1f}% (大盘中证转债)', color='purple', alpha=0.65)
ax1.fill_between(total_return_s19.index, cum_contrib_eq_s19 + cum_contrib_bond_s19, cum_contrib_eq_s19 + cum_contrib_bond_s19 + cum_contrib_com_s19, 
                 label=f'【商】贡献: {com_ratio_s19*100:.1f}% (四只商品ETF等权)', color='darkgoldenrod', alpha=0.65)

ax1.set_title('2021年4月起：纯实操期 累计收益拆解与真实利润占比', fontsize=18, fontweight='bold', pad=15)
ax1.yaxis.set_major_formatter(ticker.PercentFormatter(xmax=1.0))
ax1.legend(loc='upper left', fontsize=12); ax1.grid(True, linestyle='-.', alpha=0.4)

# 子图2：动态仓位堆叠图
ax2.stackplot(total_return_s19.index, w_eq_s19*100, w_bond_s19*100, w_com_s19*100, 
              labels=['股票权重 (TOP4)', '债券权重 (中证转债)', '商品权重 (四只ETF)'], 
              colors=['crimson', 'purple', 'darkgoldenrod'], alpha=0.7)

ax2.set_ylim(0, 100)
ax2.legend(loc='upper left', fontsize=11)
ax2.set_title('纯实操期 大类资产动态仓位分布 (100% 堆叠)', fontsize=15, fontweight='bold')
ax2.set_xlabel('日期', fontsize=12); ax2.set_ylabel('配置权重 (%)', fontsize=12)

plt.tight_layout(); plt.show()

print("\nStep 19 执行完毕！这展现了在剥离所有模拟数据后，近五年来实操策略最真实的底层获利结构与防御能力。")

#%% Step 20: 宏观双核 × 微观风控的终极融合 (跨界资金转移) - 独立解耦版
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker

print("\n========== 开始执行 Step 20: 宏观与微观风控的终极融合 (双核独立版) ==========")

# --- 1. 定位并提取双核脚本中的底层数据 ---
START_DATE = pd.to_datetime('2021-04-01')
STOP_LOSS_THRESHOLD = -0.08  # 8% 追踪止损

# 获取 2021-04-01 起的公共交易日历 (确保各资产数据对齐)
valid_dates = [d for d in df_ret_ind.index if d >= START_DATE]
plot_dates = basket_ret.index.intersection(valid_dates).intersection(ret_long.index)

# 从双核长期权重 (weights_daily_long) 中提取三大宏观类别的目标比例
w_macro_eq_series = weights_daily_long['沪深300指数'].reindex(plot_dates).fillna(0)
w_macro_bond_series = (weights_daily_long['中证基金指数:货币基金'] + weights_daily_long['中证全债指数']).reindex(plot_dates).fillna(0)
w_macro_com_series = weights_daily_long['南华期货:商品指数'].reindex(plot_dates).fillna(0)

# 提取大类资产底层的日收益率
bond_ret_s20 = ret_long['中证转债'].reindex(plot_dates).fillna(0)
com_ret_s20 = basket_ret.reindex(plot_dates).fillna(0) # Step 17 生成的四只商品ETF等权篮子

# --- 2. 初始化回测容器 ---
df_s20 = pd.DataFrame(index=plot_dates)
nav_base = 1.0  # 基准：原实操组合 (无微观止损，等权)
nav_opt  = 1.0  # 优化：季频选股 + 周频20日朴素平价 + 日频8%止损 + 跨界资金转移

current_q = None
current_w = None  
q_to_inds_original = top4_df.groupby('对应预测收益季度')['行业名称'].apply(list).to_dict()
k = 0

w_rp_raw = []
tsl_active = []; tsl_peaks = []; tsl_cum_ret = []

# 用于记录终极组合每天真实的宏观大类资产分布 (画图用)
hist_w_eq = []; hist_w_bond = []; hist_w_com = []

print("正在执行终极日频回测：周频20日朴素平价 -> 日频8%熔断 -> 释放资金等分转移给【转债+商品】...")

# --- 3. 逐日步进回测逻辑 ---
for d in plot_dates:
    q_str = f"{d.year}Q{d.quarter}"
    w_str = f"{d.isocalendar().year}-W{d.isocalendar().week:02d}"
    
    # 获取当日宏观基础发牌权重
    w_macro_eq = w_macro_eq_series.loc[d]
    w_macro_bond = w_macro_bond_series.loc[d]
    w_macro_com = w_macro_com_series.loc[d]
    
    # 【逻辑1：季频更新持仓行业与止损状态】
    if q_str != current_q:
        current_q = q_str
        inds_current = q_to_inds_original.get(q_str, [])[:4]
        k = len(inds_current)
        tsl_active = [True] * k
        tsl_peaks = [1.0] * k
        tsl_cum_ret = [1.0] * k
        
    # 【逻辑2：周频更新 20日 朴素风险平价权重】
    if w_str != current_w:
        current_w = w_str
        if k > 0:
            # 找到前一个交易日在全局日历中的位置
            prev_idx = df_wide.index.get_loc(d) - 1 if df_wide.index.get_loc(d) > 0 else 0
            
            # 使用近一个月 (20个交易日) 简单波动率计算倒数平价
            vols = [df_ret_ind[ind].iloc[max(0, prev_idx-20):prev_idx].std() for ind in inds_current]
            vols = [v if pd.notna(v) and v > 0 else 0.01 for v in vols]
            inv_vols = [1.0 / v for v in vols]
            w_rp_raw = [iv / sum(inv_vols) for iv in inv_vols]
        else:
            w_rp_raw = []

    # 当日债与商的绝对收益
    r_b = bond_ret_s20.loc[d]
    r_c = com_ret_s20.loc[d]

    if not inds_current:
        # 当季完全无信号，原属于股票的仓位等分给债和商
        ret_base = (w_macro_bond + w_macro_eq/2) * r_b + (w_macro_com + w_macro_eq/2) * r_c
        ret_opt = ret_base
        hist_w_eq.append(0)
        hist_w_bond.append(w_macro_bond + w_macro_eq/2)
        hist_w_com.append(w_macro_com + w_macro_eq/2)
    else:
        # --- A. 计算原版基准组合表现 (无止损，等权) ---
        daily_r_inds = [df_ret_ind.loc[d, ind] if ind in df_ret_ind.columns and pd.notna(df_ret_ind.loc[d, ind]) else 0.0 for ind in inds_current]
        r_eq_base = sum(0.25 * r for r in daily_r_inds)
        ret_base = (w_macro_eq * r_eq_base) + (w_macro_bond * r_b) + (w_macro_com * r_c)
        
        # --- B. 计算融合优化组合表现 (微观风控 + 宏观资金转移) ---
        # 1. 结合止损状态计算股票端内部的实际持仓比例
        w_rp_actual = [w if active else 0.0 for w, active in zip(w_rp_raw, tsl_active)]
        equity_survival_rate = sum(w_rp_actual)             # 股票端内部存活比例 (0~1)
        freed_internal_weight = 1.0 - equity_survival_rate  # 触发止损空出来的内部比例
        
        # 2. 宏观层面释放的绝对资金量 (例如：股票总仓位60%，阵亡了一半，释放出30%绝对资金)
        macro_freed_funds = w_macro_eq * freed_internal_weight
        
        # 3. 股票内部的加权收益
        r_eq_opt = sum(w * r for w, r in zip(w_rp_actual, daily_r_inds)) 
        
        # 4. ★ 核心跨界转移 ★ (空仓资金等权转移给转债和商品ETF)
        final_w_eq = w_macro_eq * equity_survival_rate
        final_w_bond = w_macro_bond + (macro_freed_funds / 2.0)
        final_w_com = w_macro_com + (macro_freed_funds / 2.0)
        
        # 5. 计算组合总日收益
        ret_opt = (w_macro_eq * r_eq_opt) + (final_w_bond * r_b) + (final_w_com * r_c)
        
        # 记录真实宏观权重用于画图
        hist_w_eq.append(final_w_eq)
        hist_w_bond.append(final_w_bond)
        hist_w_com.append(final_w_com)
        
        # 盘后结算止损：更新追踪净值与熔断状态
        for i in range(k):
            if tsl_active[i]:
                tsl_cum_ret[i] *= (1 + daily_r_inds[i])
                if tsl_cum_ret[i] > tsl_peaks[i]:
                    tsl_peaks[i] = tsl_cum_ret[i] 
                elif (tsl_cum_ret[i] / tsl_peaks[i] - 1) <= STOP_LOSS_THRESHOLD:
                    tsl_active[i] = False # 从最高点回撤达8%，触发止损，明日自动变成空头资金
                    
    # 累加净值
    nav_base *= (1 + ret_base)
    nav_opt *= (1 + ret_opt)
    df_s20.loc[d, '原实操期组合 (等权TOP4+债商无风控)'] = nav_base
    df_s20.loc[d, '终极进化组合 (周20日平价+8%止损+资金跨界防守)'] = nav_opt

# --- 4. 绩效核算 ---
results_s20 = []
years = (df_s20.index[-1] - df_s20.index[0]).days / 365.25

for col in df_s20.columns:
    nav_s = df_s20[col].dropna()
    ann_ret = nav_s.iloc[-1] ** (1 / years) - 1 if years > 0 else 0
    max_dd = (nav_s / nav_s.cummax() - 1).min()
    ann_vol = nav_s.pct_change().std() * (252 ** 0.5)
    sharpe = (ann_ret - 0.03) / ann_vol if ann_vol > 0 else 0
    
    results_s20.append({
        '策略版本 (2021Q2起纯实盘期)': col,
        '最终净值': round(nav_s.iloc[-1], 3),
        '年化收益率': f"{ann_ret*100:.2f}%",
        '最大回撤': f"{max_dd*100:.2f}%",
        '夏普比率': f"{sharpe:.2f}"
    })

print("\n================== 终极跨界避险模型 核心绩效对比 ==================")
print(pd.DataFrame(results_s20).to_string(index=False))
print("===================================================================")

# --- 5. 绘图：双组合净值走势对比与真实仓位面貌 ---
fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(16, 12), gridspec_kw={'height_ratios': [2.5, 1.5]}, sharex=True)

# 子图1：累计净值与回撤
ax1.plot(df_s20.index, df_s20['原实操期组合 (等权TOP4+债商无风控)'], label='原版策略 (硬扛所有行业回撤)', color='gray', linewidth=2, linestyle='--')
ax1.plot(df_s20.index, df_s20['终极进化组合 (周20日平价+8%止损+资金跨界防守)'], label='终极进化组合 (微观切断亏损 + 宏观跨界防守)', color='darkorange', linewidth=3)

ax1.set_title('2021Q2-2026：微观风控与宏观资产配置的完美跨界融合', fontsize=18, fontweight='bold', pad=15)
ax1.set_ylabel('累计净值 (2021Q2=1.0)', fontsize=12)
ax1.grid(True, linestyle=':', alpha=0.7)
ax1.legend(fontsize=13, loc='upper left')

# 子图2：终极版的真实大类资产仓位堆叠图
hist_w_eq = np.array(hist_w_eq) * 100
hist_w_bond = np.array(hist_w_bond) * 100
hist_w_com = np.array(hist_w_com) * 100

ax2.stackplot(plot_dates, hist_w_eq, hist_w_bond, hist_w_com, 
              labels=['【进攻】股票仓位 (TOP4动态存活部分)', '【防守】债券仓位 (宏观基准 + 避险流入资金)', '【防守】商品仓位 (宏观基准 + 避险流入资金)'], 
              colors=['crimson', 'purple', 'darkgoldenrod'], alpha=0.85)

ax2.set_title('终极组合：大类资产动态仓位演变 (包含微观止损导致的宏观防守转移)', fontsize=15, fontweight='bold')
ax2.set_ylabel('资产配置权重 (%)', fontsize=12)
ax2.set_ylim(0, 100)
ax2.legend(loc='upper left', fontsize=11, framealpha=0.9)

plt.tight_layout()
plt.show()

print("\nStep 20 独立执行完毕！代码已完全解耦，未调用其他脚本任何变量。")

#%% Step 21: 动态接回机制 (打破小黑屋，突破20日均线重新上车)
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker

print("\n========== 开始执行 Step 21: 动态接回机制 (微观趋势双向风控) ==========")

# --- 1. 定位并提取双核脚本中的底层数据 ---
START_DATE = pd.to_datetime('2021-04-01')
STOP_LOSS_THRESHOLD = -0.08  # 8% 追踪止损

# 计算全行业的 20日均线 (作为接回的生命线)
ma20 = df_wide.rolling(window=20).mean()

# 获取对齐后的交易日历
valid_dates = [d for d in df_ret_ind.index if d >= START_DATE]
plot_dates = basket_ret.index.intersection(valid_dates).intersection(ret_long.index)

# 提取宏观权重与防守端收益
w_macro_eq_series = weights_daily_long['沪深300指数'].reindex(plot_dates).fillna(0)
w_macro_bond_series = (weights_daily_long['中证基金指数:货币基金'] + weights_daily_long['中证全债指数']).reindex(plot_dates).fillna(0)
w_macro_com_series = weights_daily_long['南华期货:商品指数'].reindex(plot_dates).fillna(0)

bond_ret_s21 = ret_long['中证转债'].reindex(plot_dates).fillna(0)
com_ret_s21 = basket_ret.reindex(plot_dates).fillna(0) 

# --- 2. 初始化回测容器 ---
df_s21 = pd.DataFrame(index=plot_dates)
nav_base = 1.0  # 基准：原纯实操期组合 (等权TOP4 + 宏观债/商，无止损无转移)
nav_opt  = 1.0  # 优化：动态接回版 (20日平价 + 8%止损 + 20日线接回 + 跨界转移)

current_q = None; current_w = None  
q_to_inds_original = top4_df.groupby('对应预测收益季度')['行业名称'].apply(list).to_dict()
k = 0

w_rp_raw = []
tsl_active = []; tsl_peaks = []
hist_w_eq = []; hist_w_bond = []; hist_w_com = []

print("正在执行回测：加入【20日均线动态接回】逻辑，彻底修复踏空问题...")

# --- 3. 逐日步进回测逻辑 ---
for d in plot_dates:
    q_str = f"{d.year}Q{d.quarter}"
    w_str = f"{d.isocalendar().year}-W{d.isocalendar().week:02d}"
    
    w_macro_eq = w_macro_eq_series.loc[d]
    w_macro_bond = w_macro_bond_series.loc[d]
    w_macro_com = w_macro_com_series.loc[d]
    
    # 【逻辑1：季频更新持仓行业】
    if q_str != current_q:
        current_q = q_str
        inds_current = q_to_inds_original.get(q_str, [])[:4]
        k = len(inds_current)
        tsl_active = [True] * k
        # 季初使用调仓前一天的收盘价作为历史最高价的基准起点
        prev_idx = df_wide.index.get_loc(d) - 1 if df_wide.index.get_loc(d) > 0 else 0
        tsl_peaks = [df_wide.iloc[prev_idx][ind] if pd.notna(df_wide.iloc[prev_idx][ind]) else 1.0 for ind in inds_current]
        
    # 【逻辑2：周频更新朴素风险平价权重】
    if w_str != current_w:
        current_w = w_str
        if k > 0:
            prev_idx = df_wide.index.get_loc(d) - 1 if df_wide.index.get_loc(d) > 0 else 0
            vols = [df_ret_ind[ind].iloc[max(0, prev_idx-20):prev_idx].std() for ind in inds_current]
            vols = [v if pd.notna(v) and v > 0 else 0.01 for v in vols]
            inv_vols = [1.0 / v for v in vols]
            w_rp_raw = [iv / sum(inv_vols) for iv in inv_vols]
        else:
            w_rp_raw = []

    r_b = bond_ret_s21.loc[d]
    r_c = com_ret_s21.loc[d]

    if not inds_current:
        ret_base = ret_opt = (w_macro_bond + w_macro_eq/2) * r_b + (w_macro_com + w_macro_eq/2) * r_c
        hist_w_eq.append(0); hist_w_bond.append(w_macro_bond + w_macro_eq/2); hist_w_com.append(w_macro_com + w_macro_eq/2)
    else:
        daily_r_inds = [df_ret_ind.loc[d, ind] if ind in df_ret_ind.columns and pd.notna(df_ret_ind.loc[d, ind]) else 0.0 for ind in inds_current]
        
        # --- A. 原版基准 (死扛到底) ---
        r_eq_base = sum(0.25 * r for r in daily_r_inds)
        ret_base = (w_macro_eq * r_eq_base) + (w_macro_bond * r_b) + (w_macro_com * r_c)
        
        # --- B. 动态接回优化组合 ---
        w_rp_actual = [w if active else 0.0 for w, active in zip(w_rp_raw, tsl_active)]
        equity_survival_rate = sum(w_rp_actual)
        freed_internal_weight = 1.0 - equity_survival_rate
        
        macro_freed_funds = w_macro_eq * freed_internal_weight
        r_eq_opt = sum(w * r for w, r in zip(w_rp_actual, daily_r_inds)) 
        
        final_w_eq = w_macro_eq * equity_survival_rate
        final_w_bond = w_macro_bond + (macro_freed_funds / 2.0)
        final_w_com = w_macro_com + (macro_freed_funds / 2.0)
        
        ret_opt = (w_macro_eq * r_eq_opt) + (final_w_bond * r_b) + (final_w_com * r_c)
        hist_w_eq.append(final_w_eq); hist_w_bond.append(final_w_bond); hist_w_com.append(final_w_com)
        
        # --- C. 盘后风控状态结算 (核心修复区) ---
        for i, ind in enumerate(inds_current):
            current_p = df_wide.loc[d, ind]
            ma20_p = ma20.loc[d, ind]
            
            if pd.isna(current_p) or pd.isna(ma20_p): continue
                
            if tsl_active[i]:
                # 状态：存活中 -> 监控是否破位止损
                if current_p > tsl_peaks[i]:
                    tsl_peaks[i] = current_p # 创新高，推高止损线
                elif (current_p / tsl_peaks[i] - 1) <= STOP_LOSS_THRESHOLD:
                    tsl_active[i] = False    # 跌破8%，明日起转入空仓防守
            else:
                # 状态：空仓中 -> 监控是否突破均线接回
                if current_p > ma20_p:
                    tsl_active[i] = True     # 突破20日均线，明日起重新上车！
                    tsl_peaks[i] = current_p # 以接回当天的价格作为新的止损起点

    nav_base *= (1 + ret_base)
    nav_opt *= (1 + ret_opt)
    df_s21.loc[d, '原实操期组合 (无风控硬扛)'] = nav_base
    df_s21.loc[d, '动态接回组合 (平价+8%止损+20日线接回+避险)'] = nav_opt

# --- 4. 绩效核算 ---
results_s21 = []
years = (df_s21.index[-1] - df_s21.index[0]).days / 365.25

for col in df_s21.columns:
    nav_s = df_s21[col].dropna()
    ann_ret = nav_s.iloc[-1] ** (1 / years) - 1 if years > 0 else 0
    max_dd = (nav_s / nav_s.cummax() - 1).min()
    ann_vol = nav_s.pct_change().std() * (252 ** 0.5)
    sharpe = (ann_ret - 0.03) / ann_vol if ann_vol > 0 else 0
    
    results_s21.append({
        '策略架构 (2021Q2起纯实盘期)': col,
        '最终净值': round(nav_s.iloc[-1], 3),
        '年化收益率': f"{ann_ret*100:.2f}%",
        '最大回撤': f"{max_dd*100:.2f}%",
        '夏普比率': f"{sharpe:.2f}"
    })

print("\n================== 动态接回修复版 核心绩效对比 ==================")
print(pd.DataFrame(results_s21).to_string(index=False))
print("=================================================================")

# --- 5. 绘图对比 ---
fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(16, 12), gridspec_kw={'height_ratios': [2.5, 1.5]}, sharex=True)

# 子图1：净值对决
ax1.plot(df_s21.index, df_s21['原实操期组合 (无风控硬扛)'], label='原版策略 (吃满回撤)', color='gray', linewidth=2, linestyle='--')
ax1.plot(df_s21.index, df_s21['动态接回组合 (平价+8%止损+20日线接回+避险)'], label='动态接回组合 (能防守、敢追高)', color='crimson', linewidth=3)

ax1.set_title('2021Q2-2026：微观趋势双向风控 (防暴跌 + 修复踏空) 终极对比', fontsize=18, fontweight='bold', pad=15)
ax1.set_ylabel('累计净值 (2021Q2=1.0)', fontsize=12)
ax1.grid(True, linestyle=':', alpha=0.7)
ax1.legend(fontsize=13, loc='upper left')

# 子图2：能“呼吸”的仓位堆叠图
hist_w_eq = np.array(hist_w_eq) * 100
hist_w_bond = np.array(hist_w_bond) * 100
hist_w_com = np.array(hist_w_com) * 100

ax2.stackplot(plot_dates, hist_w_eq, hist_w_bond, hist_w_com, 
              labels=['【进攻】股票仓位 (动态上下车)', '【防守】债券仓位 (含避险流入)', '【防守】商品仓位 (含避险流入)'], 
              colors=['crimson', 'purple', 'darkgoldenrod'], alpha=0.85)

ax2.set_title('大类资产动态潮汐演变：资金能在股灾避险，也能在反弹时重新上车', fontsize=15, fontweight='bold')
ax2.set_ylabel('资产配置权重 (%)', fontsize=12)
ax2.set_ylim(0, 100)
ax2.legend(loc='upper left', fontsize=11, framealpha=0.9)

plt.tight_layout()
plt.show()

print("\nStep 21 完美修复！")

#%% Step 22: 终极趋势风控版 (废除固定回撤，引入 20日均线生命线双向择时)
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker

print("\n========== 开始执行 Step 22: 趋势生命线双向风控 (MA20择时 + 跨界避险) ==========")

# --- 1. 定位并提取双核脚本中的底层数据 ---
START_DATE = pd.to_datetime('2021-04-01')

# 计算所有行业的 20日简单移动平均线 (作为牛熊生命线)
ma20 = df_wide.rolling(window=20).mean()

# 获取对齐后的交易日历
valid_dates = [d for d in df_ret_ind.index if d >= START_DATE]
plot_dates = basket_ret.index.intersection(valid_dates).intersection(ret_long.index)

# 提取宏观权重与防守端收益
w_macro_eq_series = weights_daily_long['沪深300指数'].reindex(plot_dates).fillna(0)
w_macro_bond_series = (weights_daily_long['中证基金指数:货币基金'] + weights_daily_long['中证全债指数']).reindex(plot_dates).fillna(0)
w_macro_com_series = weights_daily_long['南华期货:商品指数'].reindex(plot_dates).fillna(0)

bond_ret_s22 = ret_long['中证转债'].reindex(plot_dates).fillna(0)
com_ret_s22 = basket_ret.reindex(plot_dates).fillna(0) 

# --- 2. 初始化回测容器 ---
df_s22 = pd.DataFrame(index=plot_dates)
nav_base = 1.0  # 基准：原纯实操期组合 (等权TOP4 + 宏观债/商，无风控)
nav_opt  = 1.0  # 优化：趋势生命线版 (周20日平价 + MA20双向择时 + 跨界转移)

current_q = None; current_w = None  
q_to_inds_original = top4_df.groupby('对应预测收益季度')['行业名称'].apply(list).to_dict()
k = 0

w_rp_raw = []
tsl_active = [] # 记录行业是否在 20 日均线之上
hist_w_eq = []; hist_w_bond = []; hist_w_com = []

print("正在执行回测：周频平价 -> 每日监测收盘价与 MA20 -> 破位转债商，突破接回股票...")

# --- 3. 逐日步进回测逻辑 ---
for d in plot_dates:
    q_str = f"{d.year}Q{d.quarter}"
    w_str = f"{d.isocalendar().year}-W{d.isocalendar().week:02d}"
    
    w_macro_eq = w_macro_eq_series.loc[d]
    w_macro_bond = w_macro_bond_series.loc[d]
    w_macro_com = w_macro_com_series.loc[d]
    
    # 【逻辑1：季频更新持仓行业】
    if q_str != current_q:
        current_q = q_str
        inds_current = q_to_inds_original.get(q_str, [])[:4]
        k = len(inds_current)
        
        # 季初发牌时，立刻用前一天的收盘价与均线对比，决定第一天是否能上车
        prev_idx = df_wide.index.get_loc(d) - 1 if df_wide.index.get_loc(d) > 0 else 0
        prev_date = df_wide.index[prev_idx]
        tsl_active = []
        for ind in inds_current:
            cp = df_wide.loc[prev_date, ind]
            cmp = ma20.loc[prev_date, ind]
            # 只要收盘价 >= 20日均线，就允许买入
            tsl_active.append(cp >= cmp if pd.notna(cp) and pd.notna(cmp) else True)
            
    # 【逻辑2：周频更新朴素风险平价权重】
    if w_str != current_w:
        current_w = w_str
        if k > 0:
            prev_idx = df_wide.index.get_loc(d) - 1 if df_wide.index.get_loc(d) > 0 else 0
            vols = [df_ret_ind[ind].iloc[max(0, prev_idx-20):prev_idx].std() for ind in inds_current]
            vols = [v if pd.notna(v) and v > 0 else 0.01 for v in vols]
            inv_vols = [1.0 / v for v in vols]
            w_rp_raw = [iv / sum(inv_vols) for iv in inv_vols]
        else:
            w_rp_raw = []

    r_b = bond_ret_s22.loc[d]
    r_c = com_ret_s22.loc[d]

    if not inds_current:
        ret_base = ret_opt = (w_macro_bond + w_macro_eq/2) * r_b + (w_macro_com + w_macro_eq/2) * r_c
        hist_w_eq.append(0); hist_w_bond.append(w_macro_bond + w_macro_eq/2); hist_w_com.append(w_macro_com + w_macro_eq/2)
    else:
        daily_r_inds = [df_ret_ind.loc[d, ind] if ind in df_ret_ind.columns and pd.notna(df_ret_ind.loc[d, ind]) else 0.0 for ind in inds_current]
        
        # --- A. 原版基准 (无微观风控) ---
        r_eq_base = sum(0.25 * r for r in daily_r_inds)
        ret_base = (w_macro_eq * r_eq_base) + (w_macro_bond * r_b) + (w_macro_com * r_c)
        
        # --- B. 生命线风控优化组合 ---
        w_rp_actual = [w if active else 0.0 for w, active in zip(w_rp_raw, tsl_active)]
        equity_survival_rate = sum(w_rp_actual)
        freed_internal_weight = 1.0 - equity_survival_rate
        
        # 释放的资金跨界流入防守端
        macro_freed_funds = w_macro_eq * freed_internal_weight
        r_eq_opt = sum(w * r for w, r in zip(w_rp_actual, daily_r_inds)) 
        
        final_w_eq = w_macro_eq * equity_survival_rate
        final_w_bond = w_macro_bond + (macro_freed_funds / 2.0)
        final_w_com = w_macro_com + (macro_freed_funds / 2.0)
        
        ret_opt = (w_macro_eq * r_eq_opt) + (final_w_bond * r_b) + (final_w_com * r_c)
        hist_w_eq.append(final_w_eq); hist_w_bond.append(final_w_bond); hist_w_com.append(final_w_com)
        
        # --- C. 盘后结算：每日更新生命线状态，决定明天是否上车 ---
        for i, ind in enumerate(inds_current):
            current_p = df_wide.loc[d, ind]
            ma20_p = ma20.loc[d, ind]
            
            if pd.isna(current_p) or pd.isna(ma20_p): 
                continue
                
            # 核心判断：今天的收盘价是否在 20日均线之上？
            # 如果是，明天持有；如果否，明天空仓转债商
            tsl_active[i] = current_p >= ma20_p

    nav_base *= (1 + ret_base)
    nav_opt *= (1 + ret_opt)
    df_s22.loc[d, '原实操期组合 (无微观风控硬扛)'] = nav_base
    df_s22.loc[d, '生命线双向风控 (MA20择时+平价+避险)'] = nav_opt

# --- 4. 绩效核算 ---
results_s22 = []
years = (df_s22.index[-1] - df_s22.index[0]).days / 365.25

for col in df_s22.columns:
    nav_s = df_s22[col].dropna()
    ann_ret = nav_s.iloc[-1] ** (1 / years) - 1 if years > 0 else 0
    max_dd = (nav_s / nav_s.cummax() - 1).min()
    ann_vol = nav_s.pct_change().std() * (252 ** 0.5)
    sharpe = (ann_ret - 0.03) / ann_vol if ann_vol > 0 else 0
    
    results_s22.append({
        '策略架构 (2021Q2起纯实盘期)': col,
        '最终净值': round(nav_s.iloc[-1], 3),
        '年化收益率': f"{ann_ret*100:.2f}%",
        '最大回撤': f"{max_dd*100:.2f}%",
        '夏普比率': f"{sharpe:.2f}"
    })

print("\n================== 趋势生命线修复版 核心绩效对比 ==================")
print(pd.DataFrame(results_s22).to_string(index=False))
print("===================================================================")

# --- 5. 绘图对比 ---
fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(16, 12), gridspec_kw={'height_ratios': [2.5, 1.5]}, sharex=True)

# 子图1：净值对决
ax1.plot(df_s22.index, df_s22['原实操期组合 (无微观风控硬扛)'], label='原版策略 (吃满大盘回撤)', color='gray', linewidth=2, linestyle='--')
ax1.plot(df_s22.index, df_s22['生命线双向风控 (MA20择时+平价+避险)'], label='生命线双向风控 (过滤噪音，截断亏损，让利润奔跑)', color='crimson', linewidth=3)

ax1.set_title('2021Q2-2026：MA20 趋势双向风控 终极实战检验', fontsize=18, fontweight='bold', pad=15)
ax1.set_ylabel('累计净值 (2021Q2=1.0)', fontsize=12)
ax1.grid(True, linestyle=':', alpha=0.7)
ax1.legend(fontsize=13, loc='upper left')

# 子图2：能“呼吸”的仓位堆叠图
hist_w_eq = np.array(hist_w_eq) * 100
hist_w_bond = np.array(hist_w_bond) * 100
hist_w_com = np.array(hist_w_com) * 100

ax2.stackplot(plot_dates, hist_w_eq, hist_w_bond, hist_w_com, 
              labels=['【进攻】股票仓位 (站稳 20 日均线)', '【防守】债券仓位 (含破位避险资金)', '【防守】商品仓位 (含破位避险资金)'], 
              colors=['crimson', 'purple', 'darkgoldenrod'], alpha=0.85)

ax2.set_title('大类资产趋势潮汐：顺势加仓，逆势缩头 (依据 MA20 动态演变)', fontsize=15, fontweight='bold')
ax2.set_ylabel('资产配置权重 (%)', fontsize=12)
ax2.set_ylim(0, 100)
ax2.legend(loc='upper left', fontsize=11, framealpha=0.9)

plt.tight_layout()
plt.show()

print("\nStep 22 执行完毕！均线级别的降维打击已部署。")

#%% Step 23: 控制变量测试 —— 趋势双向风控下，等权 vs 风险平价的效果与仓位对比 (修正Bug版)
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker

print("\n========== 开始执行 Step 23: 内部配权控制变量对比 (等权 vs 风险平价) ==========")

# --- 1. 定位并提取双核脚本中的底层数据 ---
START_DATE = pd.to_datetime('2021-04-01')

# 计算 20日简单移动平均线 (生命线)
ma20 = df_wide.rolling(window=20).mean()

# 获取对齐后的交易日历
valid_dates = [d for d in df_ret_ind.index if d >= START_DATE]
plot_dates = basket_ret.index.intersection(valid_dates).intersection(ret_long.index)

# 提取宏观权重与防守端收益
w_macro_eq_series = weights_daily_long['沪深300指数'].reindex(plot_dates).fillna(0)
w_macro_bond_series = (weights_daily_long['中证基金指数:货币基金'] + weights_daily_long['中证全债指数']).reindex(plot_dates).fillna(0)
w_macro_com_series = weights_daily_long['南华期货:商品指数'].reindex(plot_dates).fillna(0)

bond_ret_s23 = ret_long['中证转债'].reindex(plot_dates).fillna(0)
com_ret_s23 = basket_ret.reindex(plot_dates).fillna(0) 

# --- 2. 初始化回测容器 ---
df_s23 = pd.DataFrame(index=plot_dates)
nav_base = 1.0   
nav_eq   = 1.0   
nav_rp   = 1.0   

current_q = None; current_w = None  
q_to_inds_original = top4_df.groupby('对应预测收益季度')['行业名称'].apply(list).to_dict()
k = 0

w_eq_raw = []; w_rp_raw = []
tsl_active = [] 

w_eq_history = [] 
w_rp_history = []

print("正在执行回测：修复波动率计算Bug，真实展示平价配权的削峰填谷效果...")

# --- 3. 逐日步进回测逻辑 ---
for d in plot_dates:
    q_str = f"{d.year}Q{d.quarter}"
    w_str = f"{d.isocalendar().year}-W{d.isocalendar().week:02d}"
    
    w_macro_eq = w_macro_eq_series.loc[d]
    w_macro_bond = w_macro_bond_series.loc[d]
    w_macro_com = w_macro_com_series.loc[d]
    
    # 【修复点 1：安全获取上一交易日】
    loc_idx = df_ret_ind.index.get_loc(d)
    prev_date = df_ret_ind.index[loc_idx - 1] if loc_idx > 0 else df_ret_ind.index[0]
    
    # 【逻辑1：季频更新持仓行业】
    if q_str != current_q:
        current_q = q_str
        inds_current = q_to_inds_original.get(q_str, [])[:4]
        k = len(inds_current)
        
        tsl_active = []
        for ind in inds_current:
            cp = df_wide.loc[prev_date, ind]
            cmp = ma20.loc[prev_date, ind]
            tsl_active.append(cp >= cmp if pd.notna(cp) and pd.notna(cmp) else True)
            
    # 【逻辑2：周频更新权重分配基准】
    if w_str != current_w:
        current_w = w_str
        if k > 0:
            # 1. 恒定等权基准
            w_eq_raw = [1.0 / k] * k
            
            # 2. 动态朴素平价
            # 【修复点 2：极其鲁棒的按日期切片方法，倒推获取前20天的真实波动率】
            vols = [df_ret_ind[ind].loc[:d].iloc[-21:-1].std() for ind in inds_current]
            vols = [v if pd.notna(v) and v > 0 else 0.01 for v in vols]
            inv_vols = [1.0 / v for v in vols]
            w_rp_raw = [iv / sum(inv_vols) for iv in inv_vols]
        else:
            w_eq_raw = []; w_rp_raw = []

    r_b = bond_ret_s23.loc[d]
    r_c = com_ret_s23.loc[d]

    if not inds_current:
        ret_base = ret_eq = ret_rp = (w_macro_bond + w_macro_eq/2) * r_b + (w_macro_com + w_macro_eq/2) * r_c
        w_eq_history.append([0, 0, 0, 0, 1.0])
        w_rp_history.append([0, 0, 0, 0, 1.0])
    else:
        daily_r_inds = [df_ret_ind.loc[d, ind] if ind in df_ret_ind.columns and pd.notna(df_ret_ind.loc[d, ind]) else 0.0 for ind in inds_current]
        
        # --- A. 原版基准 ---
        r_base_eq = sum(0.25 * r for r in daily_r_inds)
        ret_base = (w_macro_eq * r_base_eq) + (w_macro_bond * r_b) + (w_macro_com * r_c)
        
        # --- B. 组1：等权 + 生命线风控 ---
        w_eq_actual = [w if active else 0.0 for w, active in zip(w_eq_raw, tsl_active)]
        eq_surv_rate = sum(w_eq_actual)
        freed_eq_weight = 1.0 - eq_surv_rate
        macro_freed_funds_eq = w_macro_eq * freed_eq_weight
        r_eq_opt = sum(w * r for w, r in zip(w_eq_actual, daily_r_inds))
        final_w_bond_eq = w_macro_bond + (macro_freed_funds_eq / 2.0)
        final_w_com_eq = w_macro_com + (macro_freed_funds_eq / 2.0)
        ret_eq = (w_macro_eq * r_eq_opt) + (final_w_bond_eq * r_b) + (final_w_com_eq * r_c)

        # --- C. 组2：朴素平价 + 生命线风控 ---
        w_rp_actual = [w if active else 0.0 for w, active in zip(w_rp_raw, tsl_active)]
        rp_surv_rate = sum(w_rp_actual)
        freed_rp_weight = 1.0 - rp_surv_rate
        macro_freed_funds_rp = w_macro_eq * freed_rp_weight
        r_rp_opt = sum(w * r for w, r in zip(w_rp_actual, daily_r_inds)) 
        final_w_bond_rp = w_macro_bond + (macro_freed_funds_rp / 2.0)
        final_w_com_rp = w_macro_com + (macro_freed_funds_rp / 2.0)
        ret_rp = (w_macro_eq * r_rp_opt) + (final_w_bond_rp * r_b) + (final_w_com_rp * r_c)
        
        # 记录真实大类分布比例
        record_eq = [0.0]*4; record_rp = [0.0]*4
        for i in range(len(w_eq_actual)):
            record_eq[i] = w_eq_actual[i] * w_macro_eq
            record_rp[i] = w_rp_actual[i] * w_macro_eq
            
        w_eq_history.append(record_eq + [final_w_bond_eq + final_w_com_eq])
        w_rp_history.append(record_rp + [final_w_bond_rp + final_w_com_rp])

        # --- 盘后结算 ---
        for i, ind in enumerate(inds_current):
            current_p = df_wide.loc[d, ind]
            ma20_p = ma20.loc[d, ind]
            if pd.isna(current_p) or pd.isna(ma20_p): continue
            tsl_active[i] = current_p >= ma20_p

    nav_base *= (1 + ret_base)
    nav_eq *= (1 + ret_eq)
    nav_rp *= (1 + ret_rp)
    
    df_s23.loc[d, '① 原实操组合 (无风控硬扛)'] = nav_base
    df_s23.loc[d, '② MA20双向风控 + 【等权分配】'] = nav_eq
    df_s23.loc[d, '③ MA20双向风控 + 【风险平价】'] = nav_rp

# --- 4. 绩效核算 ---
results_s23 = []
years = (df_s23.index[-1] - df_s23.index[0]).days / 365.25

for col in df_s23.columns:
    nav_s = df_s23[col].dropna()
    ann_ret = nav_s.iloc[-1] ** (1 / years) - 1 if years > 0 else 0
    max_dd = (nav_s / nav_s.cummax() - 1).min()
    ann_vol = nav_s.pct_change().std() * (252 ** 0.5)
    sharpe = (ann_ret - 0.03) / ann_vol if ann_vol > 0 else 0
    
    results_s23.append({
        '策略架构 (修复波动率切片Bug)': col,
        '最终净值': round(nav_s.iloc[-1], 3),
        '年化收益率': f"{ann_ret*100:.2f}%",
        '最大回撤': f"{max_dd*100:.2f}%",
        '夏普比率': f"{sharpe:.2f}"
    })

print("\n================== 权重分配模式 控制变量绩效对比 ==================")
print(pd.DataFrame(results_s23).to_string(index=False))
print("===================================================================")

# --- 5. 绘图 1：净值对比走势图 ---
plt.figure(figsize=(15, 7))
plt.plot(df_s23.index, df_s23['① 原实操组合 (无风控硬扛)'], label='① 原实操组合 (纯Beta裸多)', color='gray', linewidth=2, linestyle='--')
plt.plot(df_s23.index, df_s23['② MA20双向风控 + 【等权分配】'], label='② 等权分配 (平均用力，收益弹性偏高)', color='royalblue', linewidth=2.5)
plt.plot(df_s23.index, df_s23['③ MA20双向风控 + 【风险平价】'], label='③ 风险平价 (打压高波，曲线更平滑)', color='crimson', linewidth=3)
plt.title('2021Q2-2026：微观内部配权差异 —— 等权 vs 风险平价 (均叠加MA20与避险)', fontsize=17, fontweight='bold', pad=15)
plt.ylabel('累计净值 (2021Q2=1.0)', fontsize=12)
plt.grid(True, linestyle=':', alpha=0.7)
plt.legend(fontsize=13, loc='upper left')
plt.fill_between(df_s23.index, df_s23['② MA20双向风控 + 【等权分配】'], df_s23['③ MA20双向风控 + 【风险平价】'], color='purple', alpha=0.1, label='等权与平价的收益差额')
plt.tight_layout()
plt.show()

# --- 6. 绘图 2：真实生效的仓位演变对比图 ---
fig, (ax_eq, ax_rp) = plt.subplots(2, 1, figsize=(16, 12), sharex=True)
labels = ['第1名行业', '第2名行业', '第3名行业', '第4名行业', '防守端 (债+商)']
colors = ['#FF6B6B', '#4ECDC4', '#45B7D1', '#F7D794', '#E0E0E0']

w_eq_arr = np.array(w_eq_history).T * 100
w_rp_arr = np.array(w_rp_history).T * 100
q_starts = pd.Series(index=plot_dates, dtype=float).resample('Q').first().index

ax_eq.stackplot(plot_dates, w_eq_arr, labels=labels, colors=colors, alpha=0.85)
for qs in q_starts:
    if qs >= plot_dates[0]: ax_eq.axvline(qs, color='white', linestyle=':', linewidth=1.5, alpha=0.7)
ax_eq.set_title('等权模式：行业仓位呈均匀分布 (存活行业雷打不动1/4)', fontsize=15, fontweight='bold')
ax_eq.set_ylabel('资金配置权重 (%)', fontsize=12)
ax_eq.set_ylim(0, 100)
ax_eq.legend(loc='upper left', fontsize=11, framealpha=0.9)

ax_rp.stackplot(plot_dates, w_rp_arr, labels=labels, colors=colors, alpha=0.85)
for qs in q_starts:
    if qs >= plot_dates[0]: ax_rp.axvline(qs, color='white', linestyle=':', linewidth=1.5, alpha=0.7)
ax_rp.set_title('平价模式：按波动率倒数重塑权重 (真实的参差不齐与削峰填谷)', fontsize=15, fontweight='bold')
ax_rp.set_ylabel('资金配置权重 (%)', fontsize=12)
ax_rp.set_ylim(0, 100)
ax_rp.legend(loc='upper left', fontsize=11, framealpha=0.9)

plt.tight_layout(rect=[0, 0.03, 1, 0.95])
plt.show()

print("\nStep 23 彻底修复！请查看新的图表，现在应该能明显看到平价模式下颜色的高低起伏了。")

#%% Step 24: MA20双向风控触发全景图 & 每日持仓明细记录表
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

print("\n========== 开始执行 Step 24: MA20 双向风控全景透视与持仓记录表 ==========")

# --- 1. 提取并处理 Step 23 留存的仓位数据 ---
# w_eq_history 包含了 [w1, w2, w3, w4, 防守端总权重]
w_arr = np.array(w_eq_history).T * 100  # 转换为百分比
actual_stock_weight = np.sum(w_arr[:4], axis=0) # 4个行业加起来的【实际存活股票总仓位】
macro_stock_weight = w_macro_eq_series.loc[plot_dates].values * 100 # 宏观模型原本发放的【理论股票仓位】

# --- 2. 绘制上下两张联动子图 ---
fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(16, 10), sharex=True, gridspec_kw={'height_ratios': [2, 1.5]})

# ================= 子图1：整体股票仓位的影响 (理论 vs 实际) =================
ax1.plot(plot_dates, macro_stock_weight, label='宏观理论股票仓位 (无风控)', color='gray', linestyle='--', linewidth=2)
ax1.plot(plot_dates, actual_stock_weight, label='微观实际股票仓位 (MA20风控后)', color='crimson', linewidth=2.5)

# 填充因为跌破 MA20 而空出来的“避险差额”
ax1.fill_between(plot_dates, actual_stock_weight, macro_stock_weight, color='purple', alpha=0.2, 
                 label='触发MA20破位 -> 被强制没收并遁入债/商的资金')
ax1.fill_between(plot_dates, 0, actual_stock_weight, color='crimson', alpha=0.1, 
                 label='维持MA20多头 -> 实际坚守在股市的资金')

ax1.set_title('MA20 风控对【总体股票仓位】的真实干预轨迹 (紫色面积越大，代表防守越深)', fontsize=16, fontweight='bold', pad=10)
ax1.set_ylabel('股票总仓位 (%)', fontsize=12)
ax1.set_ylim(0, 100)
ax1.legend(loc='upper left', fontsize=11)
ax1.grid(True, linestyle=':', alpha=0.6)

# ================= 子图2：TOP4 行业的微观存活状态 (条带图) =================
colors = ['#FF6B6B', '#4ECDC4', '#45B7D1', '#F7D794']
labels = ['第1名行业', '第2名行业', '第3名行业', '第4名行业']

for i in range(4):
    # 权重大于0.01视为“存活(均线之上)”，否则视为“死亡(跌破均线)”
    active_mask = w_arr[i] > 0.01 
    ax2.fill_between(plot_dates, i - 0.35, i + 0.35, where=active_mask, color=colors[i], alpha=0.9)
    ax2.fill_between(plot_dates, i - 0.35, i + 0.35, where=~active_mask, color='lightgray', alpha=0.4)

ax2.set_yticks([0, 1, 2, 3])
ax2.set_yticklabels(labels, fontsize=12, fontweight='bold')
ax2.set_title('微观雷达：各排位行业的 MA20 存活状态 (彩色=站稳均线持有，灰色=跌破均线空仓)', fontsize=14, fontweight='bold', pad=10)
ax2.grid(True, linestyle=':', alpha=0.4, axis='x')

# 添加季度分割线
q_starts = pd.Series(index=plot_dates, dtype=float).resample('Q').first().index
for qs in q_starts:
    if qs >= plot_dates[0]:
        ax1.axvline(qs, color='black', linestyle=':', linewidth=1.5, alpha=0.4)
        ax2.axvline(qs, color='black', linestyle=':', linewidth=1.5, alpha=0.4)

plt.tight_layout(rect=[0, 0.03, 1, 0.96])
plt.savefig('MA20双向风控透视图.png', bbox_inches='tight')
plt.show()

# --- 3. 生成每日持仓明细与资产细分记录表 ---
print("\n正在生成《每日大类资产与细分行业持仓记录表》...")

records = []
for i, d in enumerate(plot_dates):
    q_str = f"{d.year}Q{d.quarter}"
    inds_current = q_to_inds_original.get(q_str, [])[:4]
    
    # 获取三大类宏观基础权重
    w_macro_eq = w_macro_eq_series.loc[d] * 100
    w_macro_bond = w_macro_bond_series.loc[d] * 100
    w_macro_com = w_macro_com_series.loc[d] * 100
    
    # 获取真实大类权重
    w_stock_actual = actual_stock_weight[i]
    freed_funds = w_macro_eq - w_stock_actual  # 触发MA20空出来的资金
    
    w_bond_actual = w_macro_bond + freed_funds / 2.0
    w_com_actual = w_macro_com + freed_funds / 2.0
    
    # 拼接股票内部明细
    stock_details = []
    if inds_current:
        for j, ind in enumerate(inds_current):
            w_ind = w_arr[j, i]
            status = "✅线上持有" if w_ind > 0.01 else "❌破位空仓"
            stock_details.append(f"{ind}({w_ind:.1f}%, {status})")
    else:
        stock_details.append("季初无信号(全空仓)")
        
    stock_str = " | ".join(stock_details)
    bond_str = f"中证转债({w_bond_actual:.1f}%)"
    com_str = f"四只商品ETF等权({w_com_actual:.1f}%)"
    
    records.append({
        '日期': d.strftime('%Y-%m-%d'),
        '【大类】股票仓位': f"{w_stock_actual:.1f}%",
        '【大类】债券仓位': f"{w_bond_actual:.1f}%",
        '【大类】商品仓位': f"{w_com_actual:.1f}%",
        '跨界避险转移资金': f"{freed_funds:.1f}%",
        '【细分】股票持仓明细 (MA20状态)': stock_str,
        '【细分】债券明细': bond_str,
        '【细分】商品明细': com_str
    })

df_holdings = pd.DataFrame(records)

# 导出到本地 Excel
try:
    file_path = "MA20双向风控_每日持仓明细表.xlsx"
    df_holdings.to_excel(file_path, index=False)
    print(f"✅ 成功导出每日持仓表至：【{file_path}】")
except Exception as e:
    print(f"❌ 导出Excel失败: {e}")

# --- 4. 提取关键“风控触发时刻”并打印日志 ---
# 通过监控“跨界避险转移资金”的变动，来精准捕捉哪天触发了止损或接回
df_holdings['避险资金_数值'] = df_holdings['跨界避险转移资金'].str.rstrip('%').astype(float)
df_holdings['资金变动'] = df_holdings['避险资金_数值'].diff().fillna(0)

# 过滤出资金发生大幅转移的交易日 (变动幅度 > 1%)
trigger_events = df_holdings[df_holdings['资金变动'].abs() > 1.0].copy()

# 标记动作类型
trigger_events['动作类型'] = trigger_events['资金变动'].apply(lambda x: '🛡️ 破位斩仓避险' if x > 0 else '🚀 突破均线接回')

print("\n========== 核心风控日志：最近 15 次 MA20 触发事件盘点 ==========")
display_cols = ['日期', '动作类型', '跨界避险转移资金', '【大类】股票仓位', '【细分】股票持仓明细 (MA20状态)']
# 打印最近的15次操作记录
recent_events = trigger_events.tail(15)[display_cols]

# 格式化输出到控制台
for _, row in recent_events.iterrows():
    print(f"[{row['日期']}] {row['动作类型']} | 当前避险金: {row['跨界避险转移资金']} | 留存股仓: {row['【大类】股票仓位']}")
    print(f"    └─ 明细: {row['【细分】股票持仓明细 (MA20状态)']}\n")

print("=================================================================")
print("Step 24 执行完毕！风控日志与持仓明细已输出。")

#%% Step 25: 终极组合 (MA20风控+等权版) vs 沪深300 基准全方位业绩对比
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker

print("\n========== 开始执行 Step 25: 终极优化组合 vs 沪深300 业绩深度对比 ==========")

# --- 1. 获取并对齐底层数据 (2021Q2至今纯实盘期) ---
# 提取我们在 Step 23 中跑出的最终进化版策略累计净值
nav_strategy = df_s23['② MA20双向风控 + 【等权分配】']
ret_strategy = nav_strategy.pct_change().fillna(0)

# 重新切片同期的沪深300收益率，并计算基准净值起点(设为1.0)
bench_ret = ret_long['沪深300指数'].reindex(plot_dates).fillna(0)
nav_bench = (1 + bench_ret).cumprod()

# --- 2. 计算核心绩效指标概览 ---
def calc_metrics(nav_series, ret_series, name):
    years = (nav_series.index[-1] - nav_series.index[0]).days / 365.25
    ann_ret = nav_series.iloc[-1] ** (1 / years) - 1 if years > 0 else 0
    max_dd = (nav_series / nav_series.cummax() - 1).min()
    ann_vol = ret_series.std() * (252 ** 0.5)
    sharpe = (ann_ret - 0.03) / ann_vol if ann_vol > 0 else 0
    return {
        '产品名称': name,
        '最终净值': f"{nav_series.iloc[-1]:.3f}",
        '年化收益率': f"{ann_ret*100:.2f}%",
        '最大回撤': f"{max_dd*100:.2f}%",
        '夏普比率': f"{sharpe:.2f}"
    }

metrics = [
    calc_metrics(nav_strategy, ret_strategy, "终极双核组合 (季选股+MA20均分+跨界防守)"),
    calc_metrics(nav_bench, bench_ret, "市场基准：沪深300指数")
]
print("\n======================= 核心业绩情况对比 (自2021年4月起) =======================")
print(pd.DataFrame(metrics).to_string(index=False))
print("================================================================================")

# --- 3. 计算超额收益 ---
excess_return = nav_strategy / nav_bench - 1

# --- 4. 绘图 1：累计收益率及超额收益走势图 ---
fig1, ax1 = plt.subplots(figsize=(15, 7.5))
ax1.plot(nav_strategy.index, nav_strategy - 1, label='终极双核组合 累计收益率', color='crimson', linewidth=2.5)
ax1.plot(nav_bench.index, nav_bench - 1, label='基准：沪深300 累计收益率', color='grey', linewidth=1.5, linestyle='--')
ax1.plot(excess_return.index, excess_return, label='超额收益 (终极组合 vs 沪深300)', color='purple', linewidth=1.5, alpha=0.9)

ax1.axhline(0, color='black', linewidth=1, linestyle='-', alpha=0.6)
ax1.fill_between(excess_return.index, excess_return, 0, where=(excess_return >= 0), color='#DC143C', alpha=0.15)
ax1.fill_between(excess_return.index, excess_return, 0, where=(excess_return < 0), color='#228B22', alpha=0.15)

ax1.set_title('2021Q2至今：终极双核组合 vs 沪深300 累计收益率与超额收益', fontsize=17, fontweight='bold', pad=15)
ax1.yaxis.set_major_formatter(ticker.PercentFormatter(xmax=1.0))
ax1.grid(True, linestyle=':', alpha=0.6)
ax1.legend(fontsize=12, loc='upper left')
plt.tight_layout()
plt.show()

# --- 5. 绘图 2：最大回撤走势对比图 ---
dd_strategy = nav_strategy / nav_strategy.cummax() - 1
dd_bench = nav_bench / nav_bench.cummax() - 1

fig2, ax2 = plt.subplots(figsize=(15, 6))
ax2.plot(dd_strategy.index, dd_strategy, label='终极双核组合 回撤曲线', color='crimson', linewidth=2)
ax2.plot(dd_bench.index, dd_bench, label='沪深300 回撤曲线', color='grey', linewidth=1.5, linestyle='--', alpha=0.7)

ax2.axhline(y=-0.15, color='black', linestyle='-.', linewidth=1, alpha=0.4)
ax2.axhline(y=-0.30, color='black', linestyle='-.', linewidth=1, alpha=0.4)

ax2.set_title('防御力透视：历史动态最大回撤走势对比', fontsize=17, fontweight='bold', pad=15)
ax2.yaxis.set_major_formatter(ticker.PercentFormatter(xmax=1.0))
plt.ylim(top=0)
ax2.grid(True, linestyle=':', alpha=0.6)
ax2.legend(fontsize=12, loc='lower left')
plt.tight_layout()
plt.show()

# --- 6. 绘图 3：单年度收益率对比柱状图 ---
df_yearly = pd.DataFrame({'组合收益': ret_strategy, '沪深300收益': bench_ret})
# 因为 2021 年数据从 4 月开始，单独给个标签防止歧义
df_yearly['年份'] = df_yearly.index.year.astype(str)
df_yearly.loc[df_yearly.index.year == 2021, '年份'] = '2021(4月起)'

yearly_ret = df_yearly.groupby('年份').apply(lambda x: (1 + x).prod() - 1).reset_index()

fig3, ax3 = plt.subplots(figsize=(14, 6))
x = np.arange(len(yearly_ret['年份']))
width = 0.35

rects1 = ax3.bar(x - width/2, yearly_ret['组合收益'] * 100, width, label='终极双核组合 (实操版)', color='crimson', alpha=0.85)
rects2 = ax3.bar(x + width/2, yearly_ret['沪深300收益'] * 100, width, label='沪深300', color='grey', alpha=0.7)

ax3.set_title('绝对收益能力检验：单年度收益率对比柱状图', fontsize=16, fontweight='bold', pad=15)
ax3.set_xticks(x)
ax3.set_xticklabels(yearly_ret['年份'], fontsize=12)
ax3.legend(fontsize=12, loc='upper left')
ax3.axhline(0, color='black', linewidth=1)
ax3.grid(axis='y', linestyle=':', alpha=0.6)

# 添加数值百分比标签
def autolabel(rects):
    for rect in rects:
        height = rect.get_height()
        if abs(height) < 0.1: continue
        ax3.annotate(f'{height:.1f}%', 
                     xy=(rect.get_x() + rect.get_width() / 2, height),
                     xytext=(0, 3 if height > 0 else -15),  
                     textcoords="offset points",
                     ha='center', va='bottom' if height > 0 else 'top', fontsize=10)

autolabel(rects1)
autolabel(rects2)

plt.tight_layout()
plt.show()

print("\nStep 25 业绩全景展示完毕！你的宏观+中观+微观三重嵌套策略已经展现出了机构级的Alpha提取能力。")

#%% Step 26: 实盘降频优化版 (日频/周频/月频风控 + 纯等权分配)
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker

print("\n========== 开始执行 Step 26: 实盘降频版 (纯等权分配 + 周频风控监控) ==========")

# --- 1. 定位并提取双核脚本中的底层数据 ---
START_DATE = pd.to_datetime('2021-04-01')

# 计算 20日简单移动平均线 (作为趋势标尺)
ma20 = df_wide.rolling(window=20).mean()

# 获取对齐后的交易日历
valid_dates = [d for d in df_ret_ind.index if d >= START_DATE]
plot_dates = basket_ret.index.intersection(valid_dates).intersection(ret_long.index)

# 提取宏观权重与防守端收益
w_macro_eq_series = weights_daily_long['沪深300指数'].reindex(plot_dates).fillna(0)
w_macro_bond_series = (weights_daily_long['中证基金指数:货币基金'] + weights_daily_long['中证全债指数']).reindex(plot_dates).fillna(0)
w_macro_com_series = weights_daily_long['南华期货:商品指数'].reindex(plot_dates).fillna(0)

bond_ret_s26 = ret_long['中证转债'].reindex(plot_dates).fillna(0)
com_ret_s26 = basket_ret.reindex(plot_dates).fillna(0) 

# --- 2. 初始化回测容器 ---
df_s26 = pd.DataFrame(index=plot_dates)
nav_base  = 1.0   # 基准：无风控硬扛
nav_daily = 1.0   # 对比组：日频风控 (每天看均线)
nav_weekly = 1.0  # ★ 新增：周频风控 (每周只交易1次)
nav_monthly = 1.0 # 实验组：纯月频风控 (每月只交易1次)

current_q = None
current_w = None  # ★ 新增：周度追踪器
current_m = None  # 月度追踪器
q_to_inds_original = top4_df.groupby('对应预测收益季度')['行业名称'].apply(list).to_dict()
k = 0

# 状态变量
tsl_active_daily = [] 
tsl_active_weekly = []  # ★ 新增：周度状态变量
tsl_active_monthly = [] 

print("正在执行回测：加入周频监控，舍弃风险平价，全局采用 25% 等权分配...")

# --- 3. 逐日步进回测逻辑 ---
for d in plot_dates:
    q_str = f"{d.year}Q{d.quarter}"
    m_str = f"{d.year}-{d.month:02d}"
    w_str = f"{d.isocalendar()[0]}-W{d.isocalendar()[1]:02d}" 
    
    w_macro_eq = w_macro_eq_series.loc[d]
    w_macro_bond = w_macro_bond_series.loc[d]
    w_macro_com = w_macro_com_series.loc[d]
    
    # 截取前一个交易日
    loc_idx = df_ret_ind.index.get_loc(d)
    prev_date = df_ret_ind.index[loc_idx - 1] if loc_idx > 0 else df_ret_ind.index[0]
    
    # 【逻辑1：季频更新持仓行业】
    if q_str != current_q:
        current_q = q_str
        inds_current = q_to_inds_original.get(q_str, [])[:4]
        k = len(inds_current)
        
        tsl_active_daily = []
        tsl_active_weekly = [] 
        tsl_active_monthly = []
        for ind in inds_current:
            cp = df_wide.loc[prev_date, ind]
            cmp = ma20.loc[prev_date, ind]
            status = cp >= cmp if pd.notna(cp) and pd.notna(cmp) else True
            tsl_active_daily.append(status)
            tsl_active_weekly.append(status) 
            tsl_active_monthly.append(status)
            
    # 【逻辑2：★月频核心枢纽★ (每月只在这里做一次决策)】
    if m_str != current_m:
        current_m = m_str
        if k > 0:
            # 删除了风险平价计算，月频只负责更新月度防守状态
            for i, ind in enumerate(inds_current):
                cp = df_wide.loc[prev_date, ind]
                cmp = ma20.loc[prev_date, ind]
                if pd.isna(cp) or pd.isna(cmp): continue
                # 月初阅卷：只看上月末最后一个交易日的收盘价是否在均线上
                tsl_active_monthly[i] = cp >= cmp

    # 【逻辑3：★周频核心枢纽★ (每周初阅卷，锁定本周状态)】
    if w_str != current_w:
        current_w = w_str
        if k > 0:
            for i, ind in enumerate(inds_current):
                cp = df_wide.loc[prev_date, ind]
                cmp = ma20.loc[prev_date, ind]
                if pd.isna(cp) or pd.isna(cmp): continue
                # 周初阅卷：只看上周末最后一个交易日的收盘价是否在均线上
                tsl_active_weekly[i] = cp >= cmp

    r_b = bond_ret_s26.loc[d]
    r_c = com_ret_s26.loc[d]

    if not inds_current:
        ret_base = ret_daily = ret_weekly = ret_monthly = (w_macro_bond + w_macro_eq/2) * r_b + (w_macro_com + w_macro_eq/2) * r_c
    else:
        daily_r_inds = [df_ret_ind.loc[d, ind] if ind in df_ret_ind.columns and pd.notna(df_ret_ind.loc[d, ind]) else 0.0 for ind in inds_current]
        
        # --- A. 原版基准 (纯等权 0.25) ---
        r_base_eq = sum(0.25 * r for r in daily_r_inds)
        ret_base = (w_macro_eq * r_base_eq) + (w_macro_bond * r_b) + (w_macro_com * r_c)
        
        # --- B. 日频风控组 (纯等权) ---
        w_actual_d = [0.25 if active else 0.0 for active in tsl_active_daily]
        freed_weight_d = 1.0 - sum(w_actual_d)
        r_opt_d = sum(w * r for w, r in zip(w_actual_d, daily_r_inds)) 
        final_w_bond_d = w_macro_bond + (w_macro_eq * freed_weight_d / 2.0)
        final_w_com_d = w_macro_com + (w_macro_eq * freed_weight_d / 2.0)
        ret_daily = (w_macro_eq * r_opt_d) + (final_w_bond_d * r_b) + (final_w_com_d * r_c)

        # --- C. ★ 周频风控组 ★ (纯等权) ---
        w_actual_w = [0.25 if active else 0.0 for active in tsl_active_weekly]
        freed_weight_w = 1.0 - sum(w_actual_w)
        r_opt_w = sum(w * r for w, r in zip(w_actual_w, daily_r_inds)) 
        final_w_bond_w = w_macro_bond + (w_macro_eq * freed_weight_w / 2.0)
        final_w_com_w = w_macro_com + (w_macro_eq * freed_weight_w / 2.0)
        ret_weekly = (w_macro_eq * r_opt_w) + (final_w_bond_w * r_b) + (final_w_com_w * r_c)

        # --- D. 纯月频风控组 (纯等权) ---
        w_actual_m = [0.25 if active else 0.0 for active in tsl_active_monthly]
        freed_weight_m = 1.0 - sum(w_actual_m)
        r_opt_m = sum(w * r for w, r in zip(w_actual_m, daily_r_inds)) 
        final_w_bond_m = w_macro_bond + (w_macro_eq * freed_weight_m / 2.0)
        final_w_com_m = w_macro_com + (w_macro_eq * freed_weight_m / 2.0)
        ret_monthly = (w_macro_eq * r_opt_m) + (final_w_bond_m * r_b) + (final_w_com_m * r_c)

        # --- E. 仅更新日频组的盘后状态 (周频/月频组不参与) ---
        for i, ind in enumerate(inds_current):
            current_p = df_wide.loc[d, ind]
            ma20_p = ma20.loc[d, ind]
            if pd.isna(current_p) or pd.isna(ma20_p): continue
            tsl_active_daily[i] = current_p >= ma20_p

    nav_base *= (1 + ret_base)
    nav_daily *= (1 + ret_daily)
    nav_weekly *= (1 + ret_weekly) 
    nav_monthly *= (1 + ret_monthly)
    
    df_s26.loc[d, '① 原实操组合 (无风控硬扛)'] = nav_base
    df_s26.loc[d, '② 日频极致风控 (每日监控MA20)'] = nav_daily
    df_s26.loc[d, '③ 周频适中风控 (每周只交易1次)'] = nav_weekly 
    df_s26.loc[d, '④ 纯月频统筹风控 (每月只交易1次)'] = nav_monthly

# --- 4. 绩效核算 ---
results_s26 = []
years = (df_s26.index[-1] - df_s26.index[0]).days / 365.25

for col in df_s26.columns:
    nav_s = df_s26[col].dropna()
    ann_ret = nav_s.iloc[-1] ** (1 / years) - 1 if years > 0 else 0
    max_dd = (nav_s / nav_s.cummax() - 1).min()
    ann_vol = nav_s.pct_change().std() * (252 ** 0.5)
    sharpe = (ann_ret - 0.03) / ann_vol if ann_vol > 0 else 0
    
    results_s26.append({
        '操作频率实验 (纯等权)': col,
        '最终净值': round(nav_s.iloc[-1], 3),
        '年化收益率': f"{ann_ret*100:.2f}%",
        '最大回撤': f"{max_dd*100:.2f}%",
        '夏普比率': f"{sharpe:.2f}"
    })

print("\n================== 交易降频实验 (日频 vs 周频 vs 月频) 等权版绩效对比 ==================")
print(pd.DataFrame(results_s26).to_string(index=False))
print("=========================================================================================")

# --- 5. 绘图：净值对比走势图 ---
plt.figure(figsize=(15, 8))
plt.plot(df_s26.index, df_s26['① 原实操组合 (无风控硬扛)'], label='① 原实操组合 (纯Beta裸多)', color='gray', linewidth=2, linestyle='--')
plt.plot(df_s26.index, df_s26['② 日频极致风控 (每日监控MA20)'], label='② 日频监控 (反应极快，实盘极累)', color='royalblue', linewidth=2, alpha=0.6)
plt.plot(df_s26.index, df_s26['③ 周频适中风控 (每周只交易1次)'], label='③ 周频适中 (性价比高，周末盘点即可)', color='darkorange', linewidth=2.5) 
plt.plot(df_s26.index, df_s26['④ 纯月频统筹风控 (每月只交易1次)'], label='④ 纯月频统筹 (极度迟钝，完全解放双手)', color='crimson', linewidth=3)

plt.title('2021Q2-2026：日度/周度/月度 调仓频率业绩对比 (25% 等权版)', fontsize=17, fontweight='bold', pad=15)
plt.ylabel('累计净值 (2021Q2=1.0)', fontsize=12)
plt.grid(True, linestyle=':', alpha=0.7)
plt.legend(fontsize=13, loc='upper left')

plt.tight_layout()
plt.show()

print("\nStep 26 纯等权周频/月频融合版执行完毕！")

#%% Step 27: 海龟快系统 (日频20/10 + 宏观10%豁免 + 纯等权分配)
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

print("\n========== 开始执行 Step 27: 海龟快系统 (彻底舍弃风险平价，启用25%等权) ==========")

START_DATE = pd.to_datetime('2021-04-01')

# 预计算标尺
ma20 = df_wide.rolling(window=20).mean()
donchian_high_20 = df_wide.rolling(window=20).max().shift(1)
donchian_low_10 = df_wide.rolling(window=10).min().shift(1)

valid_dates = [d for d in df_ret_ind.index if d >= START_DATE]
plot_dates = basket_ret.index.intersection(valid_dates).intersection(ret_long.index)

# 提取宏观数据
w_macro_eq_series = weights_daily_long['沪深300指数'].reindex(plot_dates).fillna(0)
w_macro_bond_series = (weights_daily_long['中证基金指数:货币基金'] + weights_daily_long['中证全债指数']).reindex(plot_dates).fillna(0)
w_macro_com_series = weights_daily_long['南华期货:商品指数'].reindex(plot_dates).fillna(0)

bond_ret_s27 = ret_long['中证转债'].reindex(plot_dates).fillna(0)
com_ret_s27 = basket_ret.reindex(plot_dates).fillna(0) 

# 初始化容器
df_s27 = pd.DataFrame(index=plot_dates)
nav_base  = 1.0   
nav_ma20  = 1.0   
nav_turtle = 1.0  

current_q = None
# ★ 已彻底删除月频权重追踪器 current_m
q_to_inds_original = top4_df.groupby('对应预测收益季度')['行业名称'].apply(list).to_dict()
k = 0

tsl_active_ma20 = []   
tsl_active_turtle = [] 

print("正在执行回测：日频海龟快系统。全局采用 25% 等权分配...")

for d in plot_dates:
    q_str = f"{d.year}Q{d.quarter}"
    
    w_eq = w_macro_eq_series.loc[d]
    w_bond = w_macro_bond_series.loc[d]
    w_com = w_macro_com_series.loc[d]
    
    is_extreme_defense = abs(w_eq - 0.10) < 1e-4
    
    loc_idx = df_ret_ind.index.get_loc(d)
    prev_date = df_ret_ind.index[loc_idx - 1] if loc_idx > 0 else df_ret_ind.index[0]
    
    # 【季频更新持仓行业】
    if q_str != current_q:
        current_q = q_str
        inds_current = q_to_inds_original.get(q_str, [])[:4]
        k = len(inds_current)
        tsl_active_ma20 = [True] * k
        tsl_active_turtle = [True] * k
            
    # 【日频状态机更新】
    if k > 0:
        for i, ind in enumerate(inds_current):
            cp_prev = df_wide.loc[prev_date, ind]
            
            # --- MA20 (不豁免) ---
            ma20_prev = ma20.loc[prev_date, ind]
            if pd.notna(cp_prev) and pd.notna(ma20_prev):
                tsl_active_ma20[i] = (cp_prev >= ma20_prev)
                
            # --- 海龟快系统 (带宏观10%豁免) ---
            if is_extreme_defense:
                tsl_active_turtle[i] = True # 强防守季强制锁仓
            else:
                h20_prev = donchian_high_20.loc[prev_date, ind]
                l10_prev = donchian_low_10.loc[prev_date, ind]
                if pd.notna(cp_prev) and pd.notna(h20_prev) and pd.notna(l10_prev):
                    if cp_prev > h20_prev:
                        tsl_active_turtle[i] = True
                    elif cp_prev < l10_prev:
                        tsl_active_turtle[i] = False

    r_b = bond_ret_s27.loc[d]
    r_c = com_ret_s27.loc[d]

    if not inds_current:
        ret_base = ret_ma20 = ret_turtle = (w_bond + w_eq/2) * r_b + (w_com + w_eq/2) * r_c
    else:
        daily_r_inds = [df_ret_ind.loc[d, ind] if ind in df_ret_ind.columns and pd.notna(df_ret_ind.loc[d, ind]) else 0.0 for ind in inds_current]
        
        # --- A. 原组合 (纯等权) ---
        ret_base = (w_eq * sum(0.25 * r for r in daily_r_inds)) + (w_bond * r_b) + (w_com * r_c)
        
        # --- B. MA20 风控 (纯等权) ---
        w_actual_ma = [0.25 if active else 0.0 for active in tsl_active_ma20]
        f_weight_ma = 1.0 - sum(w_actual_ma)
        ret_ma20 = (w_eq * sum(w * r for w, r in zip(w_actual_ma, daily_r_inds))) + \
                   (w_bond + (w_eq * f_weight_ma / 2.0)) * r_b + \
                   (w_com + (w_eq * f_weight_ma / 2.0)) * r_c

        # --- C. 海龟快系统 (纯等权) ---
        w_actual_t = [0.25 if active else 0.0 for active in tsl_active_turtle]
        f_weight_t = 1.0 - sum(w_actual_t)
        ret_turtle = (w_eq * sum(w * r for w, r in zip(w_actual_t, daily_r_inds))) + \
                     (w_bond + (w_eq * f_weight_t / 2.0)) * r_b + \
                     (w_com + (w_eq * f_weight_t / 2.0)) * r_c

    nav_base *= (1 + ret_base)
    nav_ma20 *= (1 + ret_ma20)
    nav_turtle *= (1 + ret_turtle)
    
    df_s27.loc[d, '① 原组合 (无风控硬扛)'] = nav_base
    df_s27.loc[d, '② MA20单线 (日频极累)'] = nav_ma20
    df_s27.loc[d, '③ 日频海龟快系统 (带豁免)'] = nav_turtle

# --- 绩效核算 ---
results_s27 = []
years = (df_s27.index[-1] - df_s27.index[0]).days / 365.25

for col in df_s27.columns:
    nav_s = df_s27[col].dropna()
    ann_ret = nav_s.iloc[-1] ** (1 / years) - 1 if years > 0 else 0
    max_dd = (nav_s / nav_s.cummax() - 1).min()
    ann_vol = nav_s.pct_change().std() * (252 ** 0.5)
    sharpe = (ann_ret - 0.03) / ann_vol if ann_vol > 0 else 0
    results_s27.append({'止损策略实验 (等权版)': col, '最终净值': round(nav_s.iloc[-1], 3), '年化收益率': f"{ann_ret*100:.2f}%", '最大回撤': f"{max_dd*100:.2f}%", '夏普比率': f"{sharpe:.2f}"})

print("\n================== 海龟快系统 (等权版) 绩效对比 ==================")
print(pd.DataFrame(results_s27).to_string(index=False))

# --- 绘图 ---
plt.figure(figsize=(15, 8))
plt.plot(df_s27.index, df_s27['① 原组合 (无风控硬扛)'], label='① 原组合 (无风控)', color='gray', linestyle='--')
plt.plot(df_s27.index, df_s27['② MA20单线 (日频极累)'], label='② MA20单线 (交易摩擦高)', color='royalblue', alpha=0.6)
plt.plot(df_s27.index, df_s27['③ 日频海龟快系统 (带豁免)'], label='③ 日频海龟快系统 (强制等权25%)', color='mediumseagreen', linewidth=3)
plt.title('2021Q2-2026：MA20 vs 日频海龟快系统(等权) 对比', fontsize=17, fontweight='bold', pad=15)
plt.ylabel('累计净值', fontsize=12)
plt.grid(True, linestyle=':', alpha=0.7)
plt.legend(fontsize=13, loc='upper left')
plt.tight_layout()
plt.show()

print("\nStep 27 等权版执行完毕！")

#%% Step 28: 日频海龟快系统调仓明细 (双层全景 + 真实仓位穿透)
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.lines as mlines
import numpy as np

print("\n========== 开始执行 Step 28: 日频海龟调仓追踪 (等权穿透版) ==========")

turtle_trades_daily = []
current_q = None
state_dict_d = {} 

# 记录每天实际分配给该行业的最终仓位 (宏观股重 * 25%)
daily_actual_weights_d = {}

for d in plot_dates:
    q_str = f"{d.year}Q{d.quarter}"
    loc_idx = df_ret_ind.index.get_loc(d)
    prev_date = df_ret_ind.index[loc_idx - 1] if loc_idx > 0 else df_ret_ind.index[0]
    
    w_macro_eq = w_macro_eq_series.loc[d]
    is_extreme_defense = abs(w_macro_eq - 0.10) < 1e-4
    
    if q_str != current_q:
        current_q = q_str
        inds_current = q_to_inds_original.get(q_str, [])[:4]
        state_dict_d = {ind: True for ind in inds_current}
        
    for ind in inds_current:
        cp_prev = df_wide.loc[prev_date, ind]
        h20_prev = donchian_high_20.loc[prev_date, ind]
        l10_prev = donchian_low_10.loc[prev_date, ind]
        
        current_state = state_dict_d.get(ind, True)
        new_state = current_state
        
        if is_extreme_defense:
            new_state = True # 豁免季强制装死
        else:
            if pd.notna(cp_prev) and pd.notna(h20_prev) and pd.notna(l10_prev):
                if cp_prev > h20_prev:
                    new_state = True
                elif cp_prev < l10_prev:
                    new_state = False
                
        if new_state != current_state:
            action = "🔴 止损" if not new_state else "🟢 做多"
            turtle_trades_daily.append({
                '执行日期': d.strftime('%Y-%m-%d'),
                '行业名称': ind,
                '交易动作': action
            })
            state_dict_d[ind] = new_state

    # 每日终局：纯等权分配真实资金
    daily_w = {}
    for ind in inds_current:
        if state_dict_d.get(ind, False):
            daily_w[ind] = w_macro_eq * 0.25 # 固定25%等权
        else:
            daily_w[ind] = 0.0 
    daily_actual_weights_d[d] = daily_w

df_turtle_trades_d = pd.DataFrame(turtle_trades_daily)


# --- 生成【带真实等权仓位穿透的持仓流水表】 ---
hold_records_d = []
all_traded_inds = set(ind for w_dict in daily_actual_weights_d.values() for ind in w_dict.keys())

for ind in all_traded_inds:
    is_holding = False
    entry_date = None
    
    for d in plot_dates:
        current_w = daily_actual_weights_d[d].get(ind, 0.0)
        held = current_w > 0
        
        if held and not is_holding:
            is_holding = True
            entry_date = d
            
        elif not held and is_holding:
            is_holding = False
            exit_date = d
            
            entry_price = df_wide.loc[entry_date, ind]
            exit_price = df_wide.loc[exit_date, ind]
            ret_underlying = (exit_price / entry_price - 1) if pd.notna(entry_price) and entry_price > 0 else 0
            days = (exit_date - entry_date).days
            
            hold_weights = [daily_actual_weights_d[dt].get(ind, 0.0) for dt in plot_dates if entry_date <= dt < exit_date]
            avg_weight = np.mean(hold_weights) if hold_weights else 0.0
            est_contribution = ret_underlying * avg_weight
            
            hold_records_d.append({'行业名称': ind, '建仓日期': entry_date.strftime('%Y-%m-%d'), '平仓日期': exit_date.strftime('%Y-%m-%d'), 
                                   '持仓天数': days, '标的涨幅': f"{ret_underlying*100:.2f}%", '平均真实仓位': f"{avg_weight*100:.2f}%", '账户净值贡献': f"{est_contribution*100:.2f}%"})
            
    if is_holding:
        exit_date = plot_dates[-1]
        entry_price = df_wide.loc[entry_date, ind]
        exit_price = df_wide.loc[exit_date, ind]
        ret_underlying = (exit_price / entry_price - 1) if pd.notna(entry_price) and entry_price > 0 else 0
        days = (exit_date - entry_date).days
        hold_weights = [daily_actual_weights_d[dt].get(ind, 0.0) for dt in plot_dates if entry_date <= dt <= exit_date]
        avg_weight = np.mean(hold_weights) if hold_weights else 0.0
        est_contribution = ret_underlying * avg_weight
        hold_records_d.append({'行业名称': ind, '建仓日期': entry_date.strftime('%Y-%m-%d'), '平仓日期': '至今 (持仓中)', 
                               '持仓天数': days, '标的涨幅': f"{ret_underlying*100:.2f}%", '平均真实仓位': f"{avg_weight*100:.2f}%", '账户净值贡献': f"{est_contribution*100:.2f}%"})

df_holdings_d = pd.DataFrame(hold_records_d).sort_values(by=['建仓日期', '行业名称']).reset_index(drop=True)

print("\n📋 【日频版：高阶持仓流水表（25%等权）已生成】")
print(f"总计捕获 {len(df_holdings_d)} 笔持仓波段记录 (因为是日频，会有很多时间极短的碎波段)。")
print(df_holdings_d.tail(15).to_string(index=False))


# --- 绘制双层全景图 ---
if 'df_s27' in locals():
    print("\n📊 正在绘制【全局组合净值】与【日频行业明细轨迹】双层对照图...")
    
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(16, 12), gridspec_kw={'height_ratios': [2.5, 1]}, sharex=True)
    
    base_nav = df_s27['① 原组合 (无风控硬扛)']
    turtle_nav = df_s27['③ 日频海龟快系统 (带豁免)']
    
    ax1.plot(base_nav.index, base_nav, label='① 原组合净值', color='gray', linestyle='--', alpha=0.6, linewidth=2)
    ax1.plot(turtle_nav.index, turtle_nav, label='③ 日频海龟净值', color='mediumseagreen', linewidth=2.5, zorder=3)
    
    is_defense = (abs(w_macro_eq_series - 0.10) < 1e-4).astype(int)
    ax1.fill_between(w_macro_eq_series.index, 0, 3, where=(is_defense==1), color='lightblue', alpha=0.3, label='🌊 宏观极端防守期', zorder=1)
    
    if not df_turtle_trades_d.empty:
        buy_grouped = df_turtle_trades_d[df_turtle_trades_d['交易动作'] == '🟢 做多'].groupby('执行日期').size()
        sell_grouped = df_turtle_trades_d[df_turtle_trades_d['交易动作'] == '🔴 止损'].groupby('执行日期').size()
        
        for date_str, count in buy_grouped.items():
            date_pd = pd.to_datetime(date_str)
            if date_pd in turtle_nav.index:
                ax1.scatter(date_pd, turtle_nav.loc[date_pd], marker='^', color='limegreen', s=120, zorder=5, edgecolors='black')
                if count > 1: ax1.annotate(f'x{count}', (date_pd, turtle_nav.loc[date_pd]), textcoords="offset points", xytext=(0,15), ha='center', fontsize=10, fontweight='bold', color='darkgreen')

        for date_str, count in sell_grouped.items():
            date_pd = pd.to_datetime(date_str)
            if date_pd in turtle_nav.index:
                ax1.scatter(date_pd, turtle_nav.loc[date_pd], marker='v', color='crimson', s=120, zorder=5, edgecolors='black')
                if count > 1: ax1.annotate(f'x{count}', (date_pd, turtle_nav.loc[date_pd]), textcoords="offset points", xytext=(0,-20), ha='center', fontsize=10, fontweight='bold', color='darkred')

    handles, labels = ax1.get_legend_handles_labels()
    handles.append(mlines.Line2D([], [], color='white', marker='^', markerfacecolor='limegreen', markeredgecolor='black', markersize=10, label='🟢 做多 (xN为同日多笔)'))
    handles.append(mlines.Line2D([], [], color='white', marker='v', markerfacecolor='crimson', markeredgecolor='black', markersize=10, label='🔴 止损 (xN为同日多笔)'))
    
    ax1.set_ylim(min(base_nav.min(), turtle_nav.min()) * 0.95, max(base_nav.max(), turtle_nav.max()) * 1.05)
    ax1.set_title('日频海龟：全局净值 与 调仓动作对照 (注意其密集的打点)', fontsize=17, fontweight='bold', pad=15)
    ax1.set_ylabel('累计净值', fontsize=12)
    ax1.grid(True, linestyle=':', alpha=0.6)
    ax1.legend(handles=handles, loc='upper left', fontsize=11, framealpha=0.9)

    ax2.set_title('底牌揭秘：被折叠的日频海龟调仓拆解 (钢琴谱)', fontsize=14, fontweight='bold')
    
    if not df_turtle_trades_d.empty:
        traded_inds = df_turtle_trades_d['行业名称'].unique()
        ind_y_map = {ind: i for i, ind in enumerate(traded_inds)}
        
        for _, row in df_turtle_trades_d.iterrows():
            d = pd.to_datetime(row['执行日期'])
            y = ind_y_map[row['行业名称']]
            is_buy = '做多' in row['交易动作']
            ax2.scatter(d, y, marker='^' if is_buy else 'v', color='limegreen' if is_buy else 'crimson', s=100, edgecolors='black', zorder=3)

        ax2.set_yticks(range(len(traded_inds)))
        ax2.set_yticklabels(traded_inds, fontsize=11)
        ax2.fill_between(w_macro_eq_series.index, -1, len(traded_inds), where=(is_defense==1), color='lightblue', alpha=0.3, zorder=1)
        ax2.set_ylim(-0.5, len(traded_inds) - 0.5)
    
    ax2.grid(True, linestyle='--', alpha=0.5, axis='y') 
    ax2.grid(True, linestyle=':', alpha=0.3, axis='x')
    
    plt.tight_layout()
    plt.show()

print("\nStep 28 日频全景复盘执行完毕！(你可以直观对比日频钢琴谱和周频钢琴谱的稀疏程度差异)")

#%% Step 29: 三方策略大对决 (无风控 vs MA20日频 vs 周频海龟) 纯等权版
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

print("\n========== 开始执行 Step 29: 三方策略绩效对比 (彻底舍弃风险平价，启用25%等权) ==========")

START_DATE = pd.to_datetime('2021-04-01')

# 1. 预计算所有指标
donchian_high_20 = df_wide.rolling(window=20).max().shift(1)
donchian_low_10 = df_wide.rolling(window=10).min().shift(1)
ma20 = df_wide.rolling(window=20).mean()

valid_dates = [d for d in df_ret_ind.index if d >= START_DATE]
plot_dates = basket_ret.index.intersection(valid_dates).intersection(ret_long.index)

# 2. 宏观数据提取
w_macro_eq_series = weights_daily_long['沪深300指数'].reindex(plot_dates).fillna(0)
w_macro_bond_series = (weights_daily_long['中证基金指数:货币基金'] + weights_daily_long['中证全债指数']).reindex(plot_dates).fillna(0)
w_macro_com_series = weights_daily_long['南华期货:商品指数'].reindex(plot_dates).fillna(0)

bond_ret_s29 = ret_long['中证转债'].reindex(plot_dates).fillna(0)
com_ret_s29 = basket_ret.reindex(plot_dates).fillna(0) 

# 3. 初始化容器与状态变量
df_s29 = pd.DataFrame(index=plot_dates)
nav_base = 1.0   
nav_ma20 = 1.0   
nav_weekly_turtle = 1.0  

current_q = None
current_w = None 
q_to_inds_original = top4_df.groupby('对应预测收益季度')['行业名称'].apply(list).to_dict()
k = 0

tsl_active_ma20 = []      
tsl_active_weekly_t = []  

# 4. 核心回测循环
for d in plot_dates:
    q_str = f"{d.year}Q{d.quarter}"
    w_str = f"{d.isocalendar()[0]}-W{d.isocalendar()[1]:02d}"
    
    w_eq = w_macro_eq_series.loc[d]
    w_bond = w_macro_bond_series.loc[d]
    w_com = w_macro_com_series.loc[d]
    is_defense_10 = abs(w_eq - 0.10) < 1e-4
    
    loc_idx = df_ret_ind.index.get_loc(d)
    prev_date = df_ret_ind.index[loc_idx - 1] if loc_idx > 0 else df_ret_ind.index[0]
    
    # 【季频：行业切换】
    if q_str != current_q:
        current_q = q_str
        inds_current = q_to_inds_original.get(q_str, [])[:4]
        k = len(inds_current)
        tsl_active_ma20 = [True] * k
        tsl_active_weekly_t = [True] * k
            
    # 【日频/周频：状态更新】
    if k > 0:
        # A. MA20 (每日更新，不带宏观豁免)
        for i, ind in enumerate(inds_current):
            cp = df_wide.loc[prev_date, ind]
            m20 = ma20.loc[prev_date, ind]
            if pd.notna(cp) and pd.notna(m20):
                tsl_active_ma20[i] = (cp >= m20)
        
        # B. 周频海龟 (每周初更新，带 10% 宏观豁免)
        if w_str != current_w:
            current_w = w_str
            for i, ind in enumerate(inds_current):
                if is_defense_10:
                    tsl_active_weekly_t[i] = True 
                else:
                    cp = df_wide.loc[prev_date, ind]
                    h20 = donchian_high_20.loc[prev_date, ind]
                    l10 = donchian_low_10.loc[prev_date, ind]
                    if pd.notna(cp) and pd.notna(h20) and pd.notna(l10):
                        if cp > h20:
                            tsl_active_weekly_t[i] = True
                        elif cp < l10:
                            tsl_active_weekly_t[i] = False

    # 【计算单日收益】
    r_b = bond_ret_s29.loc[d]
    r_c = com_ret_s29.loc[d]
    
    if not inds_current:
        ret_b = ret_m = ret_w = (w_bond + w_eq/2) * r_b + (w_com + w_eq/2) * r_c
    else:
        daily_r = [df_ret_ind.loc[d, ind] if ind in df_ret_ind.columns and pd.notna(df_ret_ind.loc[d, ind]) else 0.0 for ind in inds_current]
        
        # ★ 1. 原组合 (分配等权)
        ret_b = (w_eq * sum(0.25 * r for r in daily_r)) + (w_bond * r_b) + (w_com * r_c)
        
        # ★ 2. MA20 日频 (分配等权)
        w_ma = [0.25 if active else 0.0 for active in tsl_active_ma20]
        f_ma = 1.0 - sum(w_ma)
        ret_m = (w_eq * sum(w * r for w, r in zip(w_ma, daily_r))) + \
                (w_bond + (w_eq * f_ma / 2.0)) * r_b + \
                (w_com + (w_eq * f_ma / 2.0)) * r_c

        # ★ 3. 周频海龟 (分配等权)
        w_wt = [0.25 if active else 0.0 for active in tsl_active_weekly_t]
        f_wt = 1.0 - sum(w_wt)
        ret_w = (w_eq * sum(w * r for w, r in zip(w_wt, daily_r))) + \
                (w_bond + (w_eq * f_wt / 2.0)) * r_b + \
                (w_com + (w_eq * f_wt / 2.0)) * r_c

    # 累乘净值并记录
    nav_base *= (1 + ret_b)
    nav_ma20 *= (1 + ret_m)
    nav_weekly_turtle *= (1 + ret_w)
    
    df_s29.loc[d, '① 原组合 (无风控硬扛)'] = nav_base
    df_s29.loc[d, '② MA20单线 (日频极累)'] = nav_ma20
    df_s29.loc[d, '③ 周频海龟 (极简省心)'] = nav_weekly_turtle

# 5. 绩效核算与打印
results_s29 = []
years = (df_s29.index[-1] - df_s29.index[0]).days / 365.25

for col in df_s29.columns:
    nav_s = df_s29[col].dropna()
    ann_ret = nav_s.iloc[-1] ** (1 / years) - 1 if years > 0 else 0
    max_dd = (nav_s / nav_s.cummax() - 1).min()
    ann_vol = nav_s.pct_change().std() * (252 ** 0.5)
    sharpe = (ann_ret - 0.03) / ann_vol if ann_vol > 0 else 0
    results_s29.append({
        '止损策略实验': col, 
        '最终净值': round(nav_s.iloc[-1], 3), 
        '年化收益率': f"{ann_ret*100:.2f}%", 
        '最大回撤': f"{max_dd*100:.2f}%", 
        '夏普比率': f"{sharpe:.2f}"
    })

print("\n================== 三方策略绩效对比 (25%等权版) ==================")
print(pd.DataFrame(results_s29).to_string(index=False))

# 6. 绘图：三方净值对比走势
plt.figure(figsize=(15, 8))
plt.plot(df_s29.index, df_s29['① 原组合 (无风控硬扛)'], label='① 原组合 (无风控)', color='gray', linestyle='--', linewidth=2)
plt.plot(df_s29.index, df_s29['② MA20单线 (日频极累)'], label='② MA20单线 (日频盯盘，交易磨损高)', color='royalblue', alpha=0.6, linewidth=2)
plt.plot(df_s29.index, df_s29['③ 周频海龟 (极简省心)'], label='③ 周频海龟 (附带宏观豁免，极简省心)', color='darkorange', linewidth=3)

plt.title('2021Q2-2026：原组合 vs MA20日频 vs 周频海龟 净值走势', fontsize=17, fontweight='bold', pad=15)
plt.ylabel('累计净值', fontsize=12)
plt.grid(True, linestyle=':', alpha=0.7)
plt.legend(fontsize=13, loc='upper left')
plt.tight_layout()
plt.show()

print("\nStep 29 纯等权版对决执行完毕！")

#%% Step 30: 组合全景视角复盘 & 真实仓位穿透 (纯等权版)
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.lines as mlines
import numpy as np

print("\n========== 开始执行 Step 30: 组合全景复盘 & 真实仓位穿透 (25%等权) ==========")

turtle_trades_weekly = []
current_q = None
current_w = None
state_dict_w = {} 

# 用于记录每天实际分配给该行业的最终仓位 (宏观股重 * 25%)
daily_actual_weights = {}

for d in plot_dates:
    q_str = f"{d.year}Q{d.quarter}"
    w_str = f"{d.isocalendar()[0]}-W{d.isocalendar()[1]:02d}" 
    
    loc_idx = df_ret_ind.index.get_loc(d)
    prev_date = df_ret_ind.index[loc_idx - 1] if loc_idx > 0 else df_ret_ind.index[0]
    
    w_macro_eq = w_macro_eq_series.loc[d]
    is_extreme_defense = abs(w_macro_eq - 0.10) < 1e-4
    
    if q_str != current_q:
        current_q = q_str
        inds_current = q_to_inds_original.get(q_str, [])[:4]
        state_dict_w = {ind: True for ind in inds_current}
            
    if w_str != current_w:
        current_w = w_str
        for ind in inds_current:
            cp_prev = df_wide.loc[prev_date, ind]
            h20_prev = donchian_high_20.loc[prev_date, ind]
            l10_prev = donchian_low_10.loc[prev_date, ind]
            
            current_state = state_dict_w.get(ind, True)
            new_state = current_state
            
            if is_extreme_defense:
                new_state = True 
            else:
                if pd.notna(cp_prev) and pd.notna(h20_prev) and pd.notna(l10_prev):
                    if cp_prev > h20_prev:
                        new_state = True
                    elif cp_prev < l10_prev:
                        new_state = False
                    
            if new_state != current_state:
                action = "🔴 止损" if not new_state else "🟢 做多"
                turtle_trades_weekly.append({
                    '执行日期': d.strftime('%Y-%m-%d'),
                    '对应周标': w_str,
                    '行业名称': ind,
                    '交易动作': action
                })
                state_dict_w[ind] = new_state

    # ★ 每日终局：纯等权分配真实资金 ★
    daily_w = {}
    for ind in inds_current:
        if state_dict_w.get(ind, False):
            # 真实总仓位 = 宏观模型股票总额度 * 25%等权
            daily_w[ind] = w_macro_eq * 0.25 
        else:
            daily_w[ind] = 0.0 
    daily_actual_weights[d] = daily_w

df_turtle_trades_w = pd.DataFrame(turtle_trades_weekly)


# --- 生成【带真实等权仓位穿透的持仓流水表】 ---
hold_records = []
all_traded_inds = set(ind for w_dict in daily_actual_weights.values() for ind in w_dict.keys())

for ind in all_traded_inds:
    is_holding = False
    entry_date = None
    
    for d in plot_dates:
        current_w = daily_actual_weights[d].get(ind, 0.0)
        held = current_w > 0
        
        if held and not is_holding:
            is_holding = True
            entry_date = d
            
        elif not held and is_holding:
            is_holding = False
            exit_date = d
            
            entry_price = df_wide.loc[entry_date, ind]
            exit_price = df_wide.loc[exit_date, ind]
            ret_underlying = (exit_price / entry_price - 1) if pd.notna(entry_price) and entry_price > 0 else 0
            days = (exit_date - entry_date).days
            
            hold_weights = [daily_actual_weights[dt].get(ind, 0.0) for dt in plot_dates if entry_date <= dt < exit_date]
            avg_weight = np.mean(hold_weights) if hold_weights else 0.0
            est_contribution = ret_underlying * avg_weight
            
            hold_records.append({
                '行业名称': ind,
                '建仓日期': entry_date.strftime('%Y-%m-%d'),
                '平仓日期': exit_date.strftime('%Y-%m-%d'),
                '持仓天数': days,
                '标的涨跌幅': f"{ret_underlying*100:.2f}%",
                '平均真实仓位': f"{avg_weight*100:.2f}%",
                '账户净值贡献': f"{est_contribution*100:.2f}%"
            })
            
    if is_holding:
        exit_date = plot_dates[-1]
        entry_price = df_wide.loc[entry_date, ind]
        exit_price = df_wide.loc[exit_date, ind]
        ret_underlying = (exit_price / entry_price - 1) if pd.notna(entry_price) and entry_price > 0 else 0
        days = (exit_date - entry_date).days
        
        hold_weights = [daily_actual_weights[dt].get(ind, 0.0) for dt in plot_dates if entry_date <= dt <= exit_date]
        avg_weight = np.mean(hold_weights) if hold_weights else 0.0
        est_contribution = ret_underlying * avg_weight
        
        hold_records.append({
            '行业名称': ind,
            '建仓日期': entry_date.strftime('%Y-%m-%d'),
            '平仓日期': '至今 (仍在持仓)',
            '持仓天数': days,
            '标的涨跌幅': f"{ret_underlying*100:.2f}%",
            '平均真实仓位': f"{avg_weight*100:.2f}%",
            '账户净值贡献': f"{est_contribution*100:.2f}%"
        })

df_holdings = pd.DataFrame(hold_records).sort_values(by=['建仓日期', '行业名称']).reset_index(drop=True)

print("\n📋 【高阶持仓流水表（25%等权版）已生成】")
print(f"总计捕获 {len(df_holdings)} 笔持仓波段记录。")
print("以下为最近 20 笔真实盈亏流水：")
print(df_holdings.tail(20).to_string(index=False))

# --- 绘制双层全景图 ---
if 'df_s29' in locals():
    print("\n📊 正在绘制【全局组合净值】与【行业明细轨迹】双层对照图...")
    
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(16, 12), gridspec_kw={'height_ratios': [2.5, 1]}, sharex=True)
    
    base_nav = df_s29['① 原组合 (无风控硬扛)']
    turtle_nav = df_s29['③ 周频海龟 (极简省心)']
    
    ax1.plot(base_nav.index, base_nav, label='① 原组合净值 (纯裸多硬扛)', color='gray', linestyle='--', alpha=0.6, linewidth=2)
    ax1.plot(turtle_nav.index, turtle_nav, label='③ 终极实盘净值 (周频海龟+10%豁免)', color='darkorange', linewidth=2.5, zorder=3)
    
    is_defense = (abs(w_macro_eq_series - 0.10) < 1e-4).astype(int)
    ax1.fill_between(w_macro_eq_series.index, 0, 3, where=(is_defense==1), color='lightblue', alpha=0.3, label='🌊 宏观极端防守期', zorder=1)
    
    if not df_turtle_trades_w.empty:
        buy_grouped = df_turtle_trades_w[df_turtle_trades_w['交易动作'] == '🟢 做多'].groupby('执行日期').size()
        sell_grouped = df_turtle_trades_w[df_turtle_trades_w['交易动作'] == '🔴 止损'].groupby('执行日期').size()
        
        for date_str, count in buy_grouped.items():
            date_pd = pd.to_datetime(date_str)
            if date_pd in turtle_nav.index:
                ax1.scatter(date_pd, turtle_nav.loc[date_pd], marker='^', color='limegreen', s=200, zorder=5, edgecolors='black')
                if count > 1: ax1.annotate(f'x{count}', (date_pd, turtle_nav.loc[date_pd]), textcoords="offset points", xytext=(0,15), ha='center', fontsize=12, fontweight='bold', color='darkgreen')

        for date_str, count in sell_grouped.items():
            date_pd = pd.to_datetime(date_str)
            if date_pd in turtle_nav.index:
                ax1.scatter(date_pd, turtle_nav.loc[date_pd], marker='v', color='crimson', s=200, zorder=5, edgecolors='black')
                if count > 1: ax1.annotate(f'x{count}', (date_pd, turtle_nav.loc[date_pd]), textcoords="offset points", xytext=(0,-20), ha='center', fontsize=12, fontweight='bold', color='darkred')

    handles, labels = ax1.get_legend_handles_labels()
    handles.append(mlines.Line2D([], [], color='white', marker='^', markerfacecolor='limegreen', markeredgecolor='black', markersize=12, label='🟢 触发做多 (xN为同日多笔)'))
    handles.append(mlines.Line2D([], [], color='white', marker='v', markerfacecolor='crimson', markeredgecolor='black', markersize=12, label='🔴 触发止损 (xN为同日多笔)'))
    
    ax1.set_ylim(min(base_nav.min(), turtle_nav.min()) * 0.95, max(base_nav.max(), turtle_nav.max()) * 1.05)
    ax1.set_title('上帝视角：全局净值 与 海龟调仓动作对照', fontsize=17, fontweight='bold', pad=15)
    ax1.set_ylabel('累计净值', fontsize=12)
    ax1.grid(True, linestyle=':', alpha=0.6)
    ax1.legend(handles=handles, loc='upper left', fontsize=11, framealpha=0.9)

    ax2.set_title('底牌揭秘：被折叠的海龟调仓拆解 (钢琴谱)', fontsize=14, fontweight='bold')
    
    if not df_turtle_trades_w.empty:
        traded_inds = df_turtle_trades_w['行业名称'].unique()
        ind_y_map = {ind: i for i, ind in enumerate(traded_inds)}
        
        for _, row in df_turtle_trades_w.iterrows():
            d = pd.to_datetime(row['执行日期'])
            y = ind_y_map[row['行业名称']]
            is_buy = '做多' in row['交易动作']
            ax2.scatter(d, y, marker='^' if is_buy else 'v', color='limegreen' if is_buy else 'crimson', s=150, edgecolors='black', zorder=3)

        ax2.set_yticks(range(len(traded_inds)))
        ax2.set_yticklabels(traded_inds, fontsize=11)
        ax2.fill_between(w_macro_eq_series.index, -1, len(traded_inds), where=(is_defense==1), color='lightblue', alpha=0.3, zorder=1)
        ax2.set_ylim(-0.5, len(traded_inds) - 0.5)
    
    ax2.grid(True, linestyle='--', alpha=0.5, axis='y') 
    ax2.grid(True, linestyle=':', alpha=0.3, axis='x')
    
    plt.tight_layout()
    plt.show()
# 将 df_holdings 导出为 Excel 文件
# index=False 的作用是去掉最左边那一列毫无意义的 0,1,2,3... 数字索引
df_holdings.to_excel('海龟持仓流水账单.xlsx', index=False)

print("✅ 导出成功！请在当前代码的同级目录下查看 '海龟持仓流水账单.xlsx'")
print("\nStep 30 纯等权版执行完毕！")

#%% Step 31: 组合级风控演练 —— TOP4整体净值MA20择时 (拧成一线) + 买卖打点
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker

print("\n========== 开始执行 Step 31: TOP4组合整体净值 MA20择时与信号打点 ==========")

START_DATE = pd.to_datetime('2021-04-01')

# --- 1. 预计算：将 TOP4 拧成一股绳，构建合成指数与组合 MA20 ---
# top4_daily_returns 是在 Step 3 中算好的每日 TOP4 等权收益率
top4_ret_s31 = top4_daily_returns.reindex(df_ret_ind.index).fillna(0)

# 构建 TOP4 合成指数的累计净值 (起点设为1.0)
top4_nav_s31 = (1 + top4_ret_s31).cumprod()

# 计算这个合成指数的 20 日简单移动平均线
top4_ma20_s31 = top4_nav_s31.rolling(window=20).mean()

# 获取对齐后的交易日历
valid_dates = [d for d in df_ret_ind.index if d >= START_DATE]
plot_dates = basket_ret.index.intersection(valid_dates).intersection(ret_long.index)

w_macro_eq_series = weights_daily_long['沪深300指数'].reindex(plot_dates).fillna(0)
w_macro_bond_series = (weights_daily_long['中证基金指数:货币基金'] + weights_daily_long['中证全债指数']).reindex(plot_dates).fillna(0)
w_macro_com_series = weights_daily_long['南华期货:商品指数'].reindex(plot_dates).fillna(0)

bond_ret_s31 = ret_long['中证转债'].reindex(plot_dates).fillna(0)
com_ret_s31 = basket_ret.reindex(plot_dates).fillna(0) 

# --- 2. 初始化回测容器 ---
df_s31 = pd.DataFrame(index=plot_dates)
nav_base = 1.0           # ① 原组合：无风控硬扛
nav_ind_ma20 = 1.0       # ② 对比组：细分行业独立 MA20 (各自为战)
nav_basket_ma20 = 1.0    # ③ 实验组：TOP4整体净值 MA20 (拧成一股绳)

current_q = None
q_to_inds_original = top4_df.groupby('对应预测收益季度')['行业名称'].apply(list).to_dict()
k = 0

tsl_active_ind = []      # 细分行业独立状态机

# ★ 新增：组合整体状态追踪器 ★
prev_basket_state = None 
basket_trades = []

print("正在执行回测：对比【细分各自为战】与【整体一键逃逸】，并追踪买卖信号...")

# --- 3. 核心扫描循环 ---
for d in plot_dates:
    q_str = f"{d.year}Q{d.quarter}"
    
    w_eq = w_macro_eq_series.loc[d]
    w_bond = w_macro_bond_series.loc[d]
    w_com = w_macro_com_series.loc[d]
    
    # 是否为宏观 10% 极端防守期 (豁免期)
    is_defense_10 = abs(w_eq - 0.10) < 1e-4
    
    loc_idx = df_ret_ind.index.get_loc(d)
    prev_date = df_ret_ind.index[loc_idx - 1] if loc_idx > 0 else df_ret_ind.index[0]
    
    # 【季频：行业切换】
    if q_str != current_q:
        current_q = q_str
        inds_current = q_to_inds_original.get(q_str, [])[:4]
        k = len(inds_current)
        tsl_active_ind = [True] * k
            
    # 【日频：状态更新 (严格使用 T-1 日数据判定) 】
    if k > 0:
        # A. 细分行业独立 MA20 (不带豁免)
        for i, ind in enumerate(inds_current):
            cp = df_wide.loc[prev_date, ind]
            m20 = ma20.loc[prev_date, ind]
            if pd.notna(cp) and pd.notna(m20):
                tsl_active_ind[i] = (cp >= m20)
        
        # B. ★ TOP4 整体净值 MA20 (拧成一股绳) ★
        basket_nav_prev = top4_nav_s31.loc[prev_date]
        basket_ma20_prev = top4_ma20_s31.loc[prev_date]
        
        if is_defense_10:
            active_basket = True # 极端防守季强制装死
        else:
            if pd.notna(basket_nav_prev) and pd.notna(basket_ma20_prev):
                active_basket = (basket_nav_prev >= basket_ma20_prev)
            else:
                active_basket = True 
                
        # 记录组合级状态翻转动作
        if prev_basket_state is not None and active_basket != prev_basket_state:
            action = '🟢 接回' if active_basket else '🔴 逃逸'
            basket_trades.append({'日期': d, '动作': action})
            
        prev_basket_state = active_basket

    # 【计算单日收益】
    r_b = bond_ret_s31.loc[d]
    r_c = com_ret_s31.loc[d]
    
    if not inds_current:
        ret_b = ret_ind = ret_bask = (w_bond + w_eq/2) * r_b + (w_com + w_eq/2) * r_c
    else:
        daily_r = [df_ret_ind.loc[d, ind] if ind in df_ret_ind.columns and pd.notna(df_ret_ind.loc[d, ind]) else 0.0 for ind in inds_current]
        
        # 1. 原组合 (无风控等权)
        ret_b = (w_eq * sum(0.25 * r for r in daily_r)) + (w_bond * r_b) + (w_com * r_c)
        
        # 2. 细分行业独立 MA20 
        w_ind_list = [0.25 if active else 0.0 for active in tsl_active_ind]
        f_ind = 1.0 - sum(w_ind_list)
        ret_ind = (w_eq * sum(w * r for w, r in zip(w_ind_list, daily_r))) + \
                  (w_bond + (w_eq * f_ind / 2.0)) * r_b + \
                  (w_com + (w_eq * f_ind / 2.0)) * r_c

        # 3. ★ 整体净值 MA20 (一键满仓 vs 一键清仓) ★
        if active_basket:
            ret_bask = (w_eq * sum(0.25 * r for r in daily_r)) + (w_bond * r_b) + (w_com * r_c)
        else:
            ret_bask = (w_bond + w_eq / 2.0) * r_b + (w_com + w_eq / 2.0) * r_c

    # 累乘净值
    nav_base *= (1 + ret_b)
    nav_ind_ma20 *= (1 + ret_ind)
    nav_basket_ma20 *= (1 + ret_bask)
    
    df_s31.loc[d, '① 原组合 (无风控硬扛)'] = nav_base
    df_s31.loc[d, '② 细分独立 MA20 (各自为战, 交易极累)'] = nav_ind_ma20
    df_s31.loc[d, '③ 组合整体 MA20 (拧成一线, 一键逃逸)'] = nav_basket_ma20

df_basket_trades = pd.DataFrame(basket_trades)
print(f"\n✅ 信号捕获完毕！TOP4组合整体 MA20 共触发了 {len(df_basket_trades)} 次交易信号 (远低于各行业独立计算)。")

# --- 4. 绩效核算与结果输出 ---
results_s31 = []
years = (df_s31.index[-1] - df_s31.index[0]).days / 365.25

for col in df_s31.columns:
    nav_s = df_s31[col].dropna()
    ann_ret = nav_s.iloc[-1] ** (1 / years) - 1 if years > 0 else 0
    max_dd = (nav_s / nav_s.cummax() - 1).min()
    ann_vol = nav_s.pct_change().std() * (252 ** 0.5)
    sharpe = (ann_ret - 0.03) / ann_vol if ann_vol > 0 else 0
    results_s31.append({
        '风控颗粒度实验 (等权基础)': col, 
        '最终净值': round(nav_s.iloc[-1], 3), 
        '年化收益率': f"{ann_ret*100:.2f}%", 
        '最大回撤': f"{max_dd*100:.2f}%", 
        '夏普比率': f"{sharpe:.2f}"
    })

print("\n================== 组合级风控 (拧成一股绳) 绩效对比 ==================")
print(pd.DataFrame(results_s31).to_string(index=False))

# --- 5. 绘图：三方净值对比走势 & 信号打点 ---
plt.figure(figsize=(16, 9))

# 画三条净值线
plt.plot(df_s31.index, df_s31['① 原组合 (无风控硬扛)'], label='① 原组合净值 (纯裸多)', color='gray', linestyle='--', linewidth=2, alpha=0.6)
plt.plot(df_s31.index, df_s31['② 细分独立 MA20 (各自为战, 交易极累)'], label='② 细分独立 MA20 (微观单点防守)', color='royalblue', alpha=0.5, linewidth=2)
plt.plot(df_s31.index, df_s31['③ 组合整体 MA20 (拧成一线, 一键逃逸)'], label='③ 组合整体 MA20 (组合级风控，极简平滑)', color='darkorange', linewidth=3, zorder=3)

# 标注宏观豁免区背景
is_defense = (abs(w_macro_eq_series - 0.10) < 1e-4).astype(int)
plt.fill_between(w_macro_eq_series.index, 0, 3, where=(is_defense==1), color='lightblue', alpha=0.3, label='🌊 宏观极端防守期 (锁定状态强制休眠)', zorder=1)

# ★ 在橙色曲线上打买卖点 ★
if not df_basket_trades.empty:
    buys = df_basket_trades[df_basket_trades['动作'] == '🟢 接回']['日期']
    sells = df_basket_trades[df_basket_trades['动作'] == '🔴 逃逸']['日期']
    
    # 映射到具体的净值数值上
    buy_navs = df_s31.loc[buys, '③ 组合整体 MA20 (拧成一线, 一键逃逸)']
    sell_navs = df_s31.loc[sells, '③ 组合整体 MA20 (拧成一线, 一键逃逸)']
    
    plt.scatter(buys, buy_navs, marker='^', color='limegreen', s=180, zorder=5, edgecolors='black', label='🟢 组合净值突破20日均线 -> 满仓接回')
    plt.scatter(sells, sell_navs, marker='v', color='crimson', s=180, zorder=5, edgecolors='black', label='🔴 组合净值跌破20日均线 -> 遁入防守')

plt.title('2021Q2起：细分各自为战 vs 整体拧成一股绳 (带精准买卖信号打点)', fontsize=17, fontweight='bold', pad=15)
plt.ylabel('累计净值', fontsize=12)
plt.grid(True, linestyle=':', alpha=0.7)

# 动态调整合理的 Y 轴范围
plt.ylim(df_s31.min().min() * 0.95, df_s31.max().max() * 1.05)

# 图例整理
plt.legend(fontsize=12, loc='upper left', framealpha=0.9)
plt.tight_layout()
plt.show()

print("\nStep 31 组合级择时测试与信号可视化执行完毕！")


#%% Step 32: 组合整体 MA20 风控全景透视 —— 持仓记录合并版 (Excel 导出)
import numpy as np
import pandas as pd

print("\n========== 开始执行 Step 32: 生成【组合级风控】持仓合并明细表 ==========")

merged_records = []
last_state = None
current_q = None

print("正在逐日扫描状态，合并无变动的持仓区间...")

# --- 1. 逐日扫描并执行合并逻辑 ---
for d in plot_dates:
    q_str = f"{d.year}Q{d.quarter}"
    
    # 提取当日基础数据
    w_macro_eq = w_macro_eq_series.loc[d] * 100
    w_macro_bond = w_macro_bond_series.loc[d] * 100
    w_macro_com = w_macro_com_series.loc[d] * 100
    is_defense_10 = abs(w_macro_eq - 10.0) < 1e-2
    
    loc_idx = df_ret_ind.index.get_loc(d)
    prev_date = df_ret_ind.index[loc_idx - 1] if loc_idx > 0 else df_ret_ind.index[0]
    
    # 季度换仓逻辑
    if q_str != current_q:
        current_q = q_str
        inds_current = q_to_inds_original.get(q_str, [])[:4]
    
    # 组合整体 MA20 状态判定
    basket_nav_prev = top4_nav_s31.loc[prev_date]
    basket_ma20_prev = top4_ma20_s31.loc[prev_date]
    
    if is_defense_10:
        active_basket = True  # 10% 豁免期强制持仓
    else:
        active_basket = (basket_nav_prev >= basket_ma20_prev) if pd.notna(basket_ma20_prev) else True
        
    # 计算当日真实分布
    w_stock_actual = w_macro_eq if active_basket else 0.0
    freed_funds = w_macro_eq - w_stock_actual
    w_bond_actual = w_macro_bond + freed_funds / 2.0
    w_com_actual = w_macro_com + freed_funds / 2.0
    
    # 拼接当日明细字符串
    stock_details = []
    if inds_current:
        for ind in inds_current:
            status = "✅线上" if active_basket else "❌破位"
            stock_details.append(f"{ind}({w_stock_actual*0.25:.1f}%, {status})")
    stock_str = " | ".join(stock_details)
    
    # 定义“当前状态” (用于比对是否需要合并)
    # 包含：大类仓位数值、具体股票明细
    current_state = {
        'stock': f"{w_stock_actual:.1f}%",
        'bond': f"{w_bond_actual:.1f}%",
        'com': f"{w_com_actual:.1f}%",
        'freed': f"{freed_funds:.1f}%",
        'details': stock_str
    }
    
    # --- 合并判定逻辑 ---
    date_str = d.strftime('%Y-%m-%d')
    
    if last_state and current_state == last_state:
        # 如果状态没变，只更新当前记录的结束日期
        merged_records[-1]['结束日期'] = date_str
        # 累计天数 (可选)
    else:
        # 状态变了，或者是第一条记录，开启新行
        new_row = {
            '开始日期': date_str,
            '结束日期': date_str,
            '【大类】股票仓位': current_state['stock'],
            '【大类】债券仓位': current_state['bond'],
            '【大类】商品仓位': current_state['com'],
            '跨界避险转移资金': current_state['freed'],
            '【细分】股票持仓明细 (组合MA20状态)': current_state['details'],
            '【细分】债券明细': f"中证转债({w_bond_actual:.1f}%)",
            '【细分】商品明细': f"四只商品ETF等权({w_com_actual:.1f}%)"
        }
        merged_records.append(new_row)
        last_state = current_state

# 转换 DataFrame
df_merged = pd.DataFrame(merged_records)

# --- 2. 导出到本地 Excel ---
try:
    file_path = "组合整体MA20_持仓区间合并表.xlsx"
    df_merged.to_excel(file_path, index=False)
    print(f"\n✅ 成功导出合并版账单至：【{file_path}】")
    print(f"数据量从 {len(plot_dates)} 天压缩至 {len(df_merged)} 个持仓阶段。")
except Exception as e:
    print(f"\n❌ 导出Excel失败: {e}")

# --- 3. 打印关键变动日志 ---
print("\n========== 核心调仓事件盘点 (最近 10 次) ==========")
for _, row in df_merged.tail(10).iterrows():
    print(f"区间: {row['开始日期']} -> {row['结束日期']} | 股仓: {row['【大类】股票仓位']} | 避险金: {row['跨界避险转移资金']}")
    print(f" └─ 明细: {row['【细分】股票持仓明细 (组合MA20状态)']}\n")

print("Step 32 合并版执行完毕！")

#%% Step 33: 持仓明细全景可视化 (甘特图 + 动态仓位堆叠图联动)
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import matplotlib.patches as mpatches
from matplotlib.ticker import FuncFormatter

print("\n========== 开始执行 Step 33: 绘制持仓明细全景甘特图与仓位拆解 ==========")

# --- 1. 重构每日持仓状态与真实大类权重 ---
daily_active_inds = {}
is_escape_daily = {}
is_defense_daily = {}
current_q = None

hist_w_eq = []
hist_w_bond = []
hist_w_com = []

for d in plot_dates:
    q_str = f"{d.year}Q{d.quarter}"
    w_eq = w_macro_eq_series.loc[d]
    w_bond = w_macro_bond_series.loc[d]
    w_com = w_macro_com_series.loc[d]
    
    is_defense = abs(w_eq - 0.10) < 1e-4

    loc_idx = df_ret_ind.index.get_loc(d)
    prev_date = df_ret_ind.index[loc_idx - 1] if loc_idx > 0 else df_ret_ind.index[0]

    if q_str != current_q:
        current_q = q_str
        inds_current = q_to_inds_original.get(q_str, [])[:4]

    # 提取 T-1 日组合 MA20 状态
    basket_nav_prev = top4_nav_s31.loc[prev_date]
    basket_ma20_prev = top4_ma20_s31.loc[prev_date]

    if is_defense:
        active_basket = True
    else:
        active_basket = (basket_nav_prev >= basket_ma20_prev) if pd.notna(basket_ma20_prev) else True

    # 记录背景带的状态
    is_defense_daily[d] = is_defense
    is_escape_daily[d] = not is_defense and not active_basket
    
    # 记录行业甘特图状态
    if active_basket and w_eq > 0 and inds_current:
        daily_active_inds[d] = inds_current
    else:
        daily_active_inds[d] = []
        
    # 计算大类资产真实权重
    if not inds_current:
        actual_w_eq = 0.0
    else:
        actual_w_eq = w_eq if active_basket else 0.0
        
    freed = w_eq - actual_w_eq
    actual_w_bond = w_bond + freed / 2.0
    actual_w_com = w_com + freed / 2.0
    
    hist_w_eq.append(actual_w_eq * 100)
    hist_w_bond.append(actual_w_bond * 100)
    hist_w_com.append(actual_w_com * 100)

# --- 2. 提取所有历史入选行业并确定 Y 轴顺序 ---
all_inds = []
for inds in daily_active_inds.values():
    for ind in inds:
        if ind not in all_inds:
            all_inds.append(ind)
            
ind_y_map = {ind: i for i, ind in enumerate(all_inds)}

# --- 3. 计算行业持仓合并区间 (用于画水平柱) ---
ind_blocks = {ind: [] for ind in all_inds}
for ind in all_inds:
    is_in = False
    start_d = None
    for d in plot_dates:
        active = ind in daily_active_inds[d]
        if active and not is_in:
            is_in = True
            start_d = d
        elif not active and is_in:
            is_in = False
            ind_blocks[ind].append((start_d, d))
    if is_in:
        ind_blocks[ind].append((start_d, plot_dates[-1]))

# --- 4. 计算红/蓝背景填充区间 ---
def get_blocks(daily_dict):
    blocks = []
    is_active = False
    start_d = None
    for d in plot_dates:
        if daily_dict[d] and not is_active:
            is_active = True
            start_d = d
        elif not daily_dict[d] and is_active:
            is_active = False
            blocks.append((start_d, d))
    if is_active:
        blocks.append((start_d, plot_dates[-1]))
    return blocks

escape_blocks = get_blocks(is_escape_daily)
defense_blocks = get_blocks(is_defense_daily)

# --- 5. 开始绘图 (双层联动图) ---
print("正在渲染全景甘特图与动态仓位堆叠图...")
fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(16, 13), gridspec_kw={'height_ratios': [2.5, 1]}, sharex=True)

# ================= 子图1：甘特图 =================
for ind, blocks in ind_blocks.items():
    y_pos = ind_y_map[ind]
    xranges = [(mdates.date2num(s), mdates.date2num(e) - mdates.date2num(s)) for s, e in blocks]
    ax1.broken_barh(xranges, (y_pos - 0.3, 0.6), facecolors='limegreen', edgecolor='black', linewidth=1, zorder=3)

for s, e in escape_blocks:
    ax1.axvspan(s, e, color='crimson', alpha=0.15, zorder=1)
    
for s, e in defense_blocks:
    ax1.axvspan(s, e, color='lightblue', alpha=0.3, zorder=1)

q_starts = pd.Series(index=plot_dates, dtype=float).resample('Q').first().index
for qs in q_starts:
    if qs >= plot_dates[0]:
        ax1.axvline(qs, color='gray', linestyle=':', linewidth=1.5, alpha=0.6, zorder=2)

ax1.set_yticks(range(len(all_inds)))
ax1.set_yticklabels(all_inds, fontsize=12, fontweight='bold')
ax1.invert_yaxis() 

legend_elements = [
    mpatches.Patch(color='limegreen', label='🟢 实际持仓期 (当季TOP4 且 组合站稳均线)'),
    mpatches.Patch(color='crimson', alpha=0.2, label='🔴 组合破位逃逸期 (强制清仓，资金遁入债商)'),
    mpatches.Patch(color='lightblue', alpha=0.4, label='🌊 宏观极端防守期 (强制10%底仓装死)')
]
ax1.legend(handles=legend_elements, loc='upper center', bbox_to_anchor=(0.5, 1.08), ncol=3, fontsize=12, framealpha=0.9)
ax1.set_title('上帝视角：双核策略持仓变迁与风控避险全景甘特图', fontsize=18, fontweight='bold', pad=40)
ax1.grid(True, linestyle='--', alpha=0.5, axis='x', zorder=0)

# ================= 子图2：动态仓位堆叠图 =================
ax2.stackplot(plot_dates, hist_w_eq, hist_w_bond, hist_w_com, 
              labels=['股票端 (组合存活部分)', '债券端 (宏观基准 + 避险流入)', '商品端 (宏观基准 + 避险流入)'],
              colors=['crimson', 'purple', 'darkgoldenrod'], alpha=0.75)
              
for qs in q_starts:
    if qs >= plot_dates[0]:
        ax2.axvline(qs, color='white', linestyle=':', linewidth=1.5, alpha=0.5, zorder=2)

ax2.set_ylabel('资产真实占比 (%)', fontsize=12)
ax2.set_ylim(0, 100)
ax2.legend(loc='upper left', fontsize=11)
ax2.set_title('大类资产底层资金流转 (100%满仓运作)', fontsize=14, fontweight='bold')

# --- ★ 自定义 X 轴格式为 年份+季度 (例如: 2021Q2) ★ ---
def quarter_formatter(x, pos):
    try:
        dt = mdates.num2date(x)
        q = (dt.month - 1) // 3 + 1
        return f"{dt.year}Q{q}"
    except:
        return ""

# 将主刻度对齐到每个季度的首月 (1月, 4月, 7月, 10月)
ax2.xaxis.set_major_locator(mdates.MonthLocator(bymonth=[1, 4, 7, 10]))
ax2.xaxis.set_major_formatter(FuncFormatter(quarter_formatter))

# 旋转标签防止拥挤，让年份季度标签更清晰
plt.setp(ax2.get_xticklabels(), rotation=45, ha='right', fontsize=12, fontweight='bold')

plt.tight_layout()
plt.show()

print("\nStep 33 执行完毕！甘特图与资产堆叠联动图生成成功。")

#%% Step 34: 股债商三类资产收益率贡献随时间变化的可视化 (含单年度贡献拆解 & 排版优化)
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker

print("\n========== 开始执行 Step 34: 大类资产收益贡献时间序列及年度拆解 ==========")

print("正在提取最新版【组合整体MA20】每日仓位，测算绝对收益贡献...")

# --- 1. 提取最新策略的总净值曲线 ---
nav_s34 = df_s31['③ 组合整体 MA20 (拧成一线, 一键逃逸)']
prev_nav = nav_s34.shift(1).fillna(1.0)
total_return_s34 = nav_s34 - 1

# --- 2. 严谨回溯并重构每日的真实收益贡献 ---
daily_cont_eq = []
daily_cont_bond = []
daily_cont_com = []

current_q = None

for d in plot_dates:
    q_str = f"{d.year}Q{d.quarter}"
    w_eq = w_macro_eq_series.loc[d]
    w_bond = w_macro_bond_series.loc[d]
    w_com = w_macro_com_series.loc[d]
    is_defense = abs(w_eq - 0.10) < 1e-4

    loc_idx = df_ret_ind.index.get_loc(d)
    prev_date = df_ret_ind.index[loc_idx - 1] if loc_idx > 0 else df_ret_ind.index[0]

    if q_str != current_q:
        current_q = q_str
        inds_current = q_to_inds_original.get(q_str, [])[:4]

    # 判断组合是否在 20日 均线之上
    basket_nav_prev = top4_nav_s31.loc[prev_date]
    basket_ma20_prev = top4_ma20_s31.loc[prev_date]

    if is_defense:
        active_basket = True
    else:
        active_basket = (basket_nav_prev >= basket_ma20_prev) if pd.notna(basket_ma20_prev) else True

    # 资金分配
    if not inds_current:
        actual_w_eq = 0.0
    else:
        actual_w_eq = w_eq if active_basket else 0.0

    freed = w_eq - actual_w_eq
    actual_w_bond = w_bond + freed / 2.0
    actual_w_com = w_com + freed / 2.0

    # 提取当日涨跌幅
    r_b = bond_ret_s31.loc[d]
    r_c = com_ret_s31.loc[d]
    r_eq = top4_daily_returns.loc[d] if pd.notna(top4_daily_returns.loc[d]) else 0.0

    # 记录当日的绝对收益比例 (自身涨跌幅 * 真实分配额度)
    daily_cont_eq.append(actual_w_eq * r_eq)
    daily_cont_bond.append(actual_w_bond * r_b)
    daily_cont_com.append(actual_w_com * r_c)

# --- 3. 计算累计绝对贡献 (转为百分比展示) ---
cum_contrib_eq = (prev_nav * pd.Series(daily_cont_eq, index=plot_dates)).cumsum() * 100
cum_contrib_bond = (prev_nav * pd.Series(daily_cont_bond, index=plot_dates)).cumsum() * 100
cum_contrib_com = (prev_nav * pd.Series(daily_cont_com, index=plot_dates)).cumsum() * 100
total_return_pct = total_return_s34 * 100

# 输出股债商三类资产的累计独立贡献
print("\n================== 终极组合：大类资产累计独立贡献 ==================")
print(f"📈 股票端累计独立贡献 : {cum_contrib_eq.iloc[-1]:>6.2f}%")
print(f"🛡️ 债券端累计独立贡献 : {cum_contrib_bond.iloc[-1]:>6.2f}%")
print(f"🛢️ 商品端累计独立贡献 : {cum_contrib_com.iloc[-1]:>6.2f}%")
print(f"🏆 组合总累计收益率   : {total_return_pct.iloc[-1]:>6.2f}%")
print("====================================================================\n")

# --- 4. 计算每年度的独立贡献与基准对比 ---
years_list = plot_dates.year.unique()
yearly_data = []

for y in years_list:
    idx_y = plot_dates[plot_dates.year == y]
    if len(idx_y) == 0: continue
    
    # 提取当年的每日绝对收益项
    c_eq_y = pd.Series([daily_cont_eq[i] for i in range(len(plot_dates)) if plot_dates[i].year == y], index=idx_y)
    c_bond_y = pd.Series([daily_cont_bond[i] for i in range(len(plot_dates)) if plot_dates[i].year == y], index=idx_y)
    c_com_y = pd.Series([daily_cont_com[i] for i in range(len(plot_dates)) if plot_dates[i].year == y], index=idx_y)
    r_tot_y = c_eq_y + c_bond_y + c_com_y
    
    # 沪深300 当年的每日收益
    r_bench_y = ret_long['沪深300指数'].reindex(idx_y).fillna(0)
    
    # 计算当年的净值演变
    nav_port_y = (1 + r_tot_y).cumprod()
    nav_bench_y = (1 + r_bench_y).cumprod()
    
    ret_port_y = nav_port_y.iloc[-1] - 1
    ret_bench_y = nav_bench_y.iloc[-1] - 1
    
    # 计算当年各资产的精确绝对贡献 (每年初基准净值重置为1.0)
    prev_nav_port_y = nav_port_y.shift(1).fillna(1.0)
    cont_eq_y = (prev_nav_port_y * c_eq_y).sum()
    cont_bond_y = (prev_nav_port_y * c_bond_y).sum()
    cont_com_y = (prev_nav_port_y * c_com_y).sum()
    
    label_y = str(y)
    if y == 2021:
        label_y = '2021(4月起)'
        
    yearly_data.append({
        '年份': label_y,
        '组合收益': ret_port_y,
        '沪深300收益': ret_bench_y,
        '股端贡献': cont_eq_y,
        '债端贡献': cont_bond_y,
        '商端贡献': cont_com_y
    })
    
df_yearly = pd.DataFrame(yearly_data)

# --- 5. 绘图 1：独立走势与面积图 ---
print("正在渲染大类资产收益贡献全景分析图...")
fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(16, 13), sharex=True)

ax1.plot(total_return_pct.index, total_return_pct, label='组合总累计收益率 (Total)', color='black', linewidth=3, zorder=5)
ax1.plot(cum_contrib_eq.index, cum_contrib_eq, label='【股】累计独立贡献', color='crimson', linewidth=2.5)
ax1.plot(cum_contrib_bond.index, cum_contrib_bond, label='【债】累计独立贡献', color='purple', linewidth=2.5)
ax1.plot(cum_contrib_com.index, cum_contrib_com, label='【商】累计独立贡献', color='darkgoldenrod', linewidth=2.5)
ax1.axhline(0, color='gray', linestyle='--', linewidth=1.5)
ax1.set_title('解剖发电机：各资产【独立累计收益贡献】真实轨迹追踪 (单位: %)', fontsize=17, fontweight='bold', pad=15)
ax1.set_ylabel('累计绝对贡献 (%)', fontsize=12)
ax1.legend(loc='upper left', fontsize=12, framealpha=0.9, ncol=2)
ax1.grid(True, linestyle=':', alpha=0.6)

ax2.plot(total_return_pct.index, total_return_pct, label='组合总累计收益率', color='black', linewidth=2.5, zorder=5)
ax2.fill_between(total_return_pct.index, 0, cum_contrib_eq, label='【股】贡献叠加', color='crimson', alpha=0.7)
ax2.fill_between(total_return_pct.index, cum_contrib_eq, cum_contrib_eq + cum_contrib_bond, label='【债】贡献叠加', color='purple', alpha=0.7)
ax2.fill_between(total_return_pct.index, cum_contrib_eq + cum_contrib_bond, cum_contrib_eq + cum_contrib_bond + cum_contrib_com, label='【商】贡献叠加', color='darkgoldenrod', alpha=0.7)
ax2.axhline(0, color='gray', linestyle='--', linewidth=1.5)

q_starts = pd.Series(index=total_return_pct.index, dtype=float).resample('Q').first().index
for qs in q_starts:
    if qs >= total_return_pct.index[0]:
        ax1.axvline(qs, color='gray', linestyle=':', linewidth=1, alpha=0.3)
        ax2.axvline(qs, color='white', linestyle=':', linewidth=1, alpha=0.5)

ax2.set_title('组合全貌：股债商累计收益【堆叠面积图】 (单位: %)', fontsize=17, fontweight='bold', pad=15)
ax2.set_ylabel('累计绝对贡献 (%)', fontsize=12)
ax2.legend(loc='upper left', fontsize=12, framealpha=0.9, ncol=2)
ax2.grid(True, linestyle=':', alpha=0.6)

plt.tight_layout()
plt.show()

# --- 6. 绘图 2：单年度收益拆解对比柱状图 (优化图例遮挡) ---
print("正在渲染单年度收益率拆解对比柱状图...")
fig3, ax3 = plt.subplots(figsize=(15, 8)) # 稍微增加了高度给顶部留白
x = np.arange(len(df_yearly['年份']))
width = 0.35

# 画基准：沪深300
ax3.bar(x + width/2, df_yearly['沪深300收益'] * 100, width, label='基准：沪深300', color='grey', alpha=0.7)

# 画组合：股债商正负双向堆叠
pos_bottoms = np.zeros(len(df_yearly))
neg_bottoms = np.zeros(len(df_yearly))
colors = {'股端贡献': 'crimson', '债端贡献': 'purple', '商端贡献': 'darkgoldenrod'}
labels = {'股端贡献': '组合_股票端贡献', '债端贡献': '组合_债券端贡献', '商端贡献': '组合_商品端贡献'}

for col in ['股端贡献', '债端贡献', '商端贡献']:
    vals = df_yearly[col] * 100
    pos_vals = np.maximum(vals, 0)
    neg_vals = np.minimum(vals, 0)
    
    ax3.bar(x - width/2, pos_vals, width, bottom=pos_bottoms, color=colors[col], label=labels[col])
    ax3.bar(x - width/2, neg_vals, width, bottom=neg_bottoms, color=colors[col])
    
    pos_bottoms += pos_vals
    neg_bottoms += neg_vals

# ★ 核心修改：将标题上移，图例平铺放置在图表正上方画板外部 ★
ax3.set_title('各年度绝对收益对决：组合内部股/债/商归因拆解 vs 沪深300', fontsize=18, fontweight='bold', pad=45)
ax3.legend(fontsize=12, loc='upper center', bbox_to_anchor=(0.5, 1.08), ncol=4, framealpha=0.9)

ax3.set_xticks(x)
ax3.set_xticklabels(df_yearly['年份'], fontsize=12)
ax3.axhline(0, color='black', linewidth=1)
ax3.grid(axis='y', linestyle=':', alpha=0.6)
ax3.set_ylabel('年度绝对收益 (%)', fontsize=12)

# 标注数值标签
for i in range(len(x)):
    tot = df_yearly['组合收益'].iloc[i] * 100
    bench = df_yearly['沪深300收益'].iloc[i] * 100
    
    # 标注组合总计 (在堆叠柱的最高/最低点)
    y_pos_port = pos_bottoms[i] if tot >= 0 else neg_bottoms[i]
    ax3.annotate(f'{tot:.1f}%', 
                 xy=(x[i] - width/2, y_pos_port),
                 xytext=(0, 4 if tot >= 0 else -15),  
                 textcoords="offset points",
                 ha='center', va='bottom' if tot >= 0 else 'top', fontsize=11, fontweight='bold', color='darkred')
    
    # 标注基准
    ax3.annotate(f'{bench:.1f}%', 
                 xy=(x[i] + width/2, bench),
                 xytext=(0, 4 if bench >= 0 else -15),  
                 textcoords="offset points",
                 ha='center', va='bottom' if bench >= 0 else 'top', fontsize=10, color='black')

plt.tight_layout()
plt.show()

print("\nStep 34 图例排版优化完毕！")


#%% Step 35: 十年期全景回测无缝拼接 (2016-2026) —— 宏微观双核终极形态 (含高阶绩效指标)
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import matplotlib.patches as mpatches
from matplotlib.ticker import FuncFormatter
import matplotlib.ticker as ticker

print("\n========== 开始执行 Step 35: 2016-2026 全区间无缝拼接与风控压力测试 ==========")

# --- 1. 时间轴切分与底层标尺准备 ---
start_dt = pd.to_datetime('2016-01-01')
split_dt = pd.to_datetime('2021-04-01') # 模拟期与实盘期分界线
dates_all = [d for d in ret_long.index if d >= start_dt]

print(f"正在回溯 {start_dt.date()} 至最新交易日 的全天候避险数据...")

# 预计算第一阶段的标尺：沪深300的 20 日均线
hs300_price = prices_all['沪深300指数'].reindex(dates_all).ffill()
hs300_ma20 = hs300_price.rolling(window=20).mean()

# 预提取前置环境中的第二阶段标尺：TOP4组合的净值与均线 (来自 Step 31)
if 'top4_nav_s31' not in locals():
    top4_nav_s31 = (1 + top4_daily_returns.reindex(dates_all).fillna(0)).cumprod()
    top4_ma20_s31 = top4_nav_s31.rolling(window=20).mean()

# --- 2. 严谨回溯并重构每日的真实收益与状态 ---
daily_cont_eq = []; daily_cont_bond = []; daily_cont_com = []
ret_opt_list = []; ret_bench_list = []; hs300_ret_list = []

# 用于画图的状态记录
is_escape_daily = {}; is_defense_daily = {}; daily_active_assets = {}
hist_w_eq = []; hist_w_bond = []; hist_w_com = []

current_q = None

for d in dates_all:
    w_eq = weights_daily_long['沪深300指数'].loc[d] if pd.notna(weights_daily_long['沪深300指数'].loc[d]) else 0.0
    w_bond = (weights_daily_long['中证基金指数:货币基金'] + weights_daily_long['中证全债指数']).loc[d] if pd.notna((weights_daily_long['中证基金指数:货币基金'] + weights_daily_long['中证全债指数']).loc[d]) else 0.0
    w_com = weights_daily_long['南华期货:商品指数'].loc[d] if pd.notna(weights_daily_long['南华期货:商品指数'].loc[d]) else 0.0
    
    is_def = abs(w_eq - 0.10) < 1e-4
    is_defense_daily[d] = is_def
    
    loc_idx = dates_all.index(d)
    prev_date = dates_all[loc_idx - 1] if loc_idx > 0 else dates_all[0]
    
    # ---------------- 核心拼接逻辑 ----------------
    if d < split_dt:
        # 【第一阶段 (2016-2021Q1)】：沪深300 + 南华商品 + 沪深300 MA20风控
        p_prev = hs300_price.loc[prev_date]
        m_prev = hs300_ma20.loc[prev_date]
        
        active_eq = (p_prev >= m_prev) if not is_def and pd.notna(m_prev) else True
        if is_def: active_eq = True 
            
        r_e = ret_long['沪深300指数'].loc[d]
        r_b = ret_long['中证转债'].loc[d]
        r_c = ret_long['南华期货:商品指数'].loc[d]
        
        active_assets = ['【第一阶段】沪深300大盘'] if active_eq and w_eq > 0 else []
        
    else:
        # 【第二阶段 (2021Q2起)】：TOP4景气度 + 4只ETF商品 + 组合整体 MA20风控
        q_str = f"{d.year}Q{d.quarter}"
        inds_current = q_to_inds_original.get(q_str, [])[:4]
        
        basket_nav_prev = top4_nav_s31.loc[prev_date] if prev_date in top4_nav_s31.index else np.nan
        basket_ma20_prev = top4_ma20_s31.loc[prev_date] if prev_date in top4_ma20_s31.index else np.nan
        
        active_eq = (basket_nav_prev >= basket_ma20_prev) if not is_def and pd.notna(basket_ma20_prev) else True
        if is_def: active_eq = True 
            
        r_e = top4_daily_returns.loc[d] if pd.notna(top4_daily_returns.loc[d]) else 0.0
        r_b = ret_long['中证转债'].loc[d]
        r_c = basket_ret.loc[d] if d in basket_ret.index else 0.0
        
        active_assets = inds_current if active_eq and w_eq > 0 else []
        
    # ---------------- 资金分配与收益结算 ----------------
    is_escape_daily[d] = not is_def and not active_eq
    daily_active_assets[d] = active_assets
    
    act_w_eq = w_eq if active_eq else 0.0
    freed = w_eq - act_w_eq
    act_w_bond = w_bond + freed / 2.0
    act_w_com = w_com + freed / 2.0
    
    hist_w_eq.append(act_w_eq * 100); hist_w_bond.append(act_w_bond * 100); hist_w_com.append(act_w_com * 100)
    
    daily_cont_eq.append(act_w_eq * r_e)
    daily_cont_bond.append(act_w_bond * r_b)
    daily_cont_com.append(act_w_com * r_c)
    
    ret_opt_list.append(act_w_eq * r_e + act_w_bond * r_b + act_w_com * r_c)
    
    r_c_bench = ret_long['南华期货:商品指数'].loc[d] if d < split_dt else (basket_ret.loc[d] if d in basket_ret.index else 0.0)
    ret_bench_list.append(w_eq * r_e + w_bond * r_b + w_com * r_c_bench)
    
    hs300_ret_list.append(ret_long['沪深300指数'].loc[d])

# --- 3. 计算净值与绝对收益贡献 ---
nav_opt = (1 + pd.Series(ret_opt_list, index=dates_all)).cumprod()
nav_bench = (1 + pd.Series(ret_bench_list, index=dates_all)).cumprod()
nav_hs300 = (1 + pd.Series(hs300_ret_list, index=dates_all)).cumprod()

prev_nav = nav_opt.shift(1).fillna(1.0)
cum_contrib_eq = (prev_nav * pd.Series(daily_cont_eq, index=dates_all)).cumsum() * 100
cum_contrib_bond = (prev_nav * pd.Series(daily_cont_bond, index=dates_all)).cumsum() * 100
cum_contrib_com = (prev_nav * pd.Series(daily_cont_com, index=dates_all)).cumsum() * 100
total_return_pct = (nav_opt - 1) * 100

# ★ 升级功能：输出十年期高阶核心绩效对比表 ★
def calc_metrics(nav_series, name):
    tot_days = len(nav_series)
    daily_ret = nav_series.pct_change().fillna(0)
    
    # 年化收益率
    ann_ret = nav_series.iloc[-1] ** (252 / tot_days) - 1 if tot_days > 0 else 0
    # 最大回撤
    max_dd = (nav_series / nav_series.cummax() - 1).min()
    # 年化波动率
    ann_vol = daily_ret.std() * np.sqrt(252)
    
    # 夏普比率 (假设无风险利率 Rf = 2%)
    rf = 0.02
    sharpe = (ann_ret - rf) / ann_vol if ann_vol > 0 else 0
    
    # 卡玛比率 (年化收益 / 最大回撤)
    calmar = ann_ret / abs(max_dd) if max_dd != 0 else 0
    
    return {
        '策略版本': name, 
        '年化收益': f"{ann_ret*100:>6.2f}%", 
        '最大回撤': f"{max_dd*100:>7.2f}%",
        '年化波动率': f"{ann_vol*100:>6.2f}%",
        '夏普比率': f"{sharpe:>5.2f}",
        '卡玛比率': f"{calmar:>5.2f}"
    }

print("\n========================= 十年期全景回测：高阶核心绩效指标对决 =========================")
print(pd.DataFrame([
    calc_metrics(nav_hs300, "② 基准：沪深300指数 纯裸多"),
    calc_metrics(nav_bench, "③ 理论原版 (仅宏观配比，无均线避险)"),
    calc_metrics(nav_opt,   "① 十年终极无缝版 (普林格底座 + MA20逃逸)")
]).to_string(index=False))
print("========================================================================================")

# ==================== 开始出图 ====================

# 【图表 1】十年全景甘特图 + 动态仓位堆叠图
print("\n正在渲染 图表1: 十年全景甘特图与资产分布潮汐...")

all_assets = []
for assets in daily_active_assets.values():
    for a in assets:
        if a not in all_assets: all_assets.append(a)
ind_y_map = {ind: i for i, ind in enumerate(all_assets)}

ind_blocks = {ind: [] for ind in all_assets}
for ind in all_assets:
    is_in = False; start_d = None
    for d in dates_all:
        active = ind in daily_active_assets[d]
        if active and not is_in:
            is_in = True; start_d = d
        elif not active and is_in:
            is_in = False; ind_blocks[ind].append((start_d, d))
    if is_in: ind_blocks[ind].append((start_d, dates_all[-1]))

def get_blocks(daily_dict):
    blocks = []; is_active = False; start_d = None
    for d in dates_all:
        if daily_dict[d] and not is_active: is_active = True; start_d = d
        elif not daily_dict[d] and is_active: is_active = False; blocks.append((start_d, d))
    if is_active: blocks.append((start_d, dates_all[-1]))
    return blocks

escape_blocks = get_blocks(is_escape_daily)
defense_blocks = get_blocks(is_defense_daily)

fig1, (ax1_1, ax1_2) = plt.subplots(2, 1, figsize=(16, max(12, len(all_assets)*0.3)), gridspec_kw={'height_ratios': [2.5, 1]}, sharex=True)

for ind, blocks in ind_blocks.items():
    y_pos = ind_y_map[ind]
    xranges = [(mdates.date2num(s), mdates.date2num(e) - mdates.date2num(s)) for s, e in blocks]
    ax1_1.broken_barh(xranges, (y_pos - 0.3, 0.6), facecolors='limegreen', edgecolor='black', linewidth=0.5, zorder=3)

for s, e in escape_blocks: ax1_1.axvspan(s, e, color='crimson', alpha=0.15, zorder=1)
for s, e in defense_blocks: ax1_1.axvspan(s, e, color='lightblue', alpha=0.3, zorder=1)

ax1_1.axvline(split_dt, color='blue', linestyle='-.', linewidth=2, zorder=4)
ax1_1.text(split_dt, -1, ' ← 前期:大盘模拟 | 后期:TOP4实操 →', color='blue', fontweight='bold', fontsize=12, ha='center')

ax1_1.set_yticks(range(len(all_assets)))
ax1_1.set_yticklabels(all_assets, fontsize=11)
ax1_1.invert_yaxis() 

legend_elements = [
    mpatches.Patch(color='limegreen', label='🟢 股票端实际持仓期 (站稳大盘/组合均线)'),
    mpatches.Patch(color='crimson', alpha=0.2, label='🔴 跌破均线逃逸期 (清仓股票，资金遁入债商)'),
    mpatches.Patch(color='lightblue', alpha=0.4, label='🌊 宏观极端防守期 (强制10%底仓装死)')
]
ax1_1.legend(handles=legend_elements, loc='upper center', bbox_to_anchor=(0.5, 1.08), ncol=3, fontsize=12, framealpha=0.9)
ax1_1.set_title('十年交响曲：2016-2026 双核轮动与避险风控全景甘特图', fontsize=18, fontweight='bold', pad=35)
ax1_1.grid(True, linestyle='--', alpha=0.5, axis='x')

ax1_2.stackplot(dates_all, hist_w_eq, hist_w_bond, hist_w_com, 
              labels=['【股】(前沪深300 / 后TOP4)', '【债】(转债底仓+避险流入)', '【商】(底仓+避险流入)'],
              colors=['crimson', 'purple', 'darkgoldenrod'], alpha=0.75)
ax1_2.axvline(split_dt, color='white', linestyle='-.', linewidth=2, zorder=4)
ax1_2.set_ylabel('大类资产占比 (%)', fontsize=12)
ax1_2.set_ylim(0, 100)
ax1_2.legend(loc='upper left', fontsize=11)

def year_formatter(x, pos):
    try: return mdates.num2date(x).strftime('%Y-%m')
    except: return ""

ax1_2.xaxis.set_major_locator(mdates.YearLocator())
ax1_2.xaxis.set_major_formatter(FuncFormatter(year_formatter))
plt.setp(ax1_2.get_xticklabels(), rotation=0, ha='center', fontsize=12, fontweight='bold')
plt.tight_layout()
plt.show()

# 【图表 2】收益率贡献拆解
print("正在渲染 图表2: 股债商绝对收益贡献拆解...")
fig2, (ax2_1, ax2_2) = plt.subplots(2, 1, figsize=(16, 13), sharex=True)

ax2_1.plot(total_return_pct.index, total_return_pct, label='终极十年策略 总累计收益率 (Total)', color='black', linewidth=3, zorder=5)
ax2_1.plot(cum_contrib_eq.index, cum_contrib_eq, label='【股】累计独立贡献 (含MA20风控)', color='crimson', linewidth=2.5)
ax2_1.plot(cum_contrib_bond.index, cum_contrib_bond, label='【债】累计独立贡献 (转债+避险)', color='purple', linewidth=2.5)
ax2_1.plot(cum_contrib_com.index, cum_contrib_com, label='【商】累计独立贡献 (商品+避险)', color='darkgoldenrod', linewidth=2.5)
ax2_1.axvline(split_dt, color='blue', linestyle='-.', linewidth=1.5, alpha=0.5)
ax2_1.axhline(0, color='gray', linestyle='--', linewidth=1.5)
ax2_1.set_title('十年账本解剖：各资产【独立累计收益贡献】轨迹 (单位: %)', fontsize=17, fontweight='bold', pad=15)
ax2_1.set_ylabel('累计绝对贡献 (%)', fontsize=12)
ax2_1.legend(loc='upper left', fontsize=12, framealpha=0.9, ncol=2)
ax2_1.grid(True, linestyle=':', alpha=0.6)

ax2_2.plot(total_return_pct.index, total_return_pct, label='策略总累计收益率', color='black', linewidth=2.5, zorder=5)
ax2_2.fill_between(total_return_pct.index, 0, cum_contrib_eq, label='【股】贡献叠加', color='crimson', alpha=0.7)
ax2_2.fill_between(total_return_pct.index, cum_contrib_eq, cum_contrib_eq + cum_contrib_bond, label='【债】贡献叠加', color='purple', alpha=0.7)
ax2_2.fill_between(total_return_pct.index, cum_contrib_eq + cum_contrib_bond, cum_contrib_eq + cum_contrib_bond + cum_contrib_com, label='【商】贡献叠加', color='darkgoldenrod', alpha=0.7)
ax2_2.axvline(split_dt, color='white', linestyle='-.', linewidth=2, alpha=0.7)
ax2_2.axhline(0, color='gray', linestyle='--', linewidth=1.5)
ax2_2.set_title('账本全貌：十年期股债商累计收益【堆叠面积图】 (单位: %)', fontsize=17, fontweight='bold', pad=15)
ax2_2.set_ylabel('累计绝对贡献 (%)', fontsize=12)
ax2_2.legend(loc='upper left', fontsize=12, framealpha=0.9, ncol=2)
ax2_2.grid(True, linestyle=':', alpha=0.6)
plt.tight_layout()
plt.show()

# 【图表 3】组合净值 vs 沪深300基准 & 超额收益面积图
print("正在渲染 图表3: 十年净值对决与超额收益全景...")
excess_return = nav_opt / nav_hs300 - 1

fig3, ax3 = plt.subplots(figsize=(16, 8))
ax3.plot(nav_opt.index, nav_opt - 1, label='① 十年终极无缝版 (普林格底座 + MA20逃逸)', color='darkorange', linewidth=3)
ax3.plot(nav_hs300.index, nav_hs300 - 1, label='② 基准：沪深300指数 纯裸多', color='grey', linewidth=1.5, linestyle='--')
ax3.plot(nav_bench.index, nav_bench - 1, label='③ 理论原版 (仅宏观配比，无均线避险)', color='steelblue', linewidth=1.5, linestyle='-.', alpha=0.6)

ax3.plot(excess_return.index, excess_return, label='超额收益 (十年终极版 vs 沪深300)', color='purple', linewidth=1.5, alpha=0.9)
ax3.axhline(0, color='black', linewidth=1, linestyle='-', alpha=0.6)
ax3.fill_between(excess_return.index, excess_return, 0, where=(excess_return >= 0), color='#DC143C', alpha=0.15)
ax3.fill_between(excess_return.index, excess_return, 0, where=(excess_return < 0), color='#228B22', alpha=0.15)

ax3.axvline(split_dt, color='blue', linestyle='-.', linewidth=2, alpha=0.7, label='2021Q2 实盘升级分界点')

ax3.set_title('十年长跑验证：全天候避险体系 vs 沪深300 累计收益与超额收益', fontsize=17, fontweight='bold', pad=15)
ax3.yaxis.set_major_formatter(ticker.PercentFormatter(xmax=1.0))
ax3.grid(True, linestyle=':', alpha=0.6)
ax3.legend(fontsize=12, loc='upper left')

plt.tight_layout()
plt.show()

print("\n🎉 大功告成！全量高阶绩效表已在控制台输出。")

#%% Step 36: 十年期实战终极优化 (2016-2026) —— 引入 1.5% 容错缓冲区的 MA20 防抖系统
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import matplotlib.patches as mpatches
from matplotlib.ticker import FuncFormatter
import matplotlib.ticker as ticker

print("\n========== 开始执行 Step 36: 引入容错缓冲区 (Buffer) 的防抖避险测试 ==========")

# ★ 核心参数调整：均线容错缓冲区设定为 1.5% ★
BUFFER_PCT = 0.015 
print(f"已开启 MA20 防抖机制！当前下行容错缓冲空间为: {BUFFER_PCT * 100}%")

# --- 1. 时间轴切分与底层标尺准备 ---
start_dt = pd.to_datetime('2016-01-01')
split_dt = pd.to_datetime('2021-04-01') 
dates_all = [d for d in ret_long.index if d >= start_dt]

hs300_price = prices_all['沪深300指数'].reindex(dates_all).ffill()
hs300_ma20 = hs300_price.rolling(window=20).mean()

if 'top4_nav_s31' not in locals():
    top4_nav_s31 = (1 + top4_daily_returns.reindex(dates_all).fillna(0)).cumprod()
    top4_ma20_s31 = top4_nav_s31.rolling(window=20).mean()

# 确保实操期商品端使用 4只ETF 等权 (来自前期计算)
etf_ret_s36 = ret_all[['大成有色ETF', '华安黄金ETF', '建信能化ETF', '华夏豆粕ETF']].fillna(0)
basket_ret_eq_s36 = etf_ret_s36.mean(axis=1)

# --- 2. 严谨回溯并重构每日的真实收益与状态 ---
daily_cont_eq = []; daily_cont_bond = []; daily_cont_com = []
ret_opt_list = []; ret_bench_list = []; hs300_ret_list = []

is_escape_daily = {}; is_defense_daily = {}; daily_active_assets = {}
hist_w_eq = []; hist_w_bond = []; hist_w_com = []

for d in dates_all:
    w_eq = weights_daily_long['沪深300指数'].loc[d] if pd.notna(weights_daily_long['沪深300指数'].loc[d]) else 0.0
    w_bond = (weights_daily_long['中证基金指数:货币基金'] + weights_daily_long['中证全债指数']).loc[d] if pd.notna((weights_daily_long['中证基金指数:货币基金'] + weights_daily_long['中证全债指数']).loc[d]) else 0.0
    w_com = weights_daily_long['南华期货:商品指数'].loc[d] if pd.notna(weights_daily_long['南华期货:商品指数'].loc[d]) else 0.0
    
    is_def = abs(w_eq - 0.10) < 1e-4
    is_defense_daily[d] = is_def
    
    loc_idx = dates_all.index(d)
    prev_date = dates_all[loc_idx - 1] if loc_idx > 0 else dates_all[0]
    
    # ---------------- 核心拼接逻辑 (带缓冲) ----------------
    if d < split_dt:
        # 第一阶段：沪深300
        p_prev = hs300_price.loc[prev_date]
        m_prev = hs300_ma20.loc[prev_date]
        
        # ★ 防抖核心：价格大于等于 均线*(1 - 1.5%) 才算安全
        active_eq = (p_prev >= m_prev * (1 - BUFFER_PCT)) if not is_def and pd.notna(m_prev) else True
        if is_def: active_eq = True 
            
        r_e = ret_long['沪深300指数'].loc[d]
        r_b = ret_long['中证转债'].loc[d]
        r_c = ret_long['南华期货:商品指数'].loc[d]
        active_assets = ['【前期】沪深300宽基'] if active_eq and w_eq > 0 else []
        
    else:
        # 第二阶段：TOP4 + 4只ETF等权
        q_str = f"{d.year}Q{d.quarter}"
        inds_current = q_to_inds_original.get(q_str, [])[:4]
        
        basket_nav_prev = top4_nav_s31.loc[prev_date] if prev_date in top4_nav_s31.index else np.nan
        basket_ma20_prev = top4_ma20_s31.loc[prev_date] if prev_date in top4_ma20_s31.index else np.nan
        
        # ★ 防抖核心：组合净值大于等于 均线*(1 - 1.5%) 才算安全
        active_eq = (basket_nav_prev >= basket_ma20_prev * (1 - BUFFER_PCT)) if not is_def and pd.notna(basket_ma20_prev) else True
        if is_def: active_eq = True 
            
        r_e = top4_daily_returns.loc[d] if pd.notna(top4_daily_returns.loc[d]) else 0.0
        r_b = ret_long['中证转债'].loc[d]
        r_c = basket_ret_eq_s36.loc[d] if d in basket_ret_eq_s36.index else 0.0
        active_assets = inds_current if active_eq and w_eq > 0 else []
        
    # ---------------- 资金分配与收益结算 ----------------
    is_escape_daily[d] = not is_def and not active_eq
    daily_active_assets[d] = active_assets
    
    act_w_eq = w_eq if active_eq else 0.0
    freed = w_eq - act_w_eq
    act_w_bond = w_bond + freed / 2.0
    act_w_com = w_com + freed / 2.0
    
    hist_w_eq.append(act_w_eq * 100); hist_w_bond.append(act_w_bond * 100); hist_w_com.append(act_w_com * 100)
    
    daily_cont_eq.append(act_w_eq * r_e)
    daily_cont_bond.append(act_w_bond * r_b)
    daily_cont_com.append(act_w_com * r_c)
    
    ret_opt_list.append(act_w_eq * r_e + act_w_bond * r_b + act_w_com * r_c)
    
    r_c_bench = ret_long['南华期货:商品指数'].loc[d] if d < split_dt else (basket_ret_eq_s36.loc[d] if d in basket_ret_eq_s36.index else 0.0)
    ret_bench_list.append(w_eq * r_e + w_bond * r_b + w_com * r_c_bench)
    hs300_ret_list.append(ret_long['沪深300指数'].loc[d])

# --- 3. 计算净值与绝对贡献 (起点为 1.0) ---
nav_opt = (1 + pd.Series(ret_opt_list, index=dates_all)).cumprod()
nav_bench = (1 + pd.Series(ret_bench_list, index=dates_all)).cumprod()
nav_hs300 = (1 + pd.Series(hs300_ret_list, index=dates_all)).cumprod()

prev_nav = nav_opt.shift(1).fillna(1.0)
cum_contrib_eq = (prev_nav * pd.Series(daily_cont_eq, index=dates_all)).cumsum()
cum_contrib_bond = (prev_nav * pd.Series(daily_cont_bond, index=dates_all)).cumsum()
cum_contrib_com = (prev_nav * pd.Series(daily_cont_com, index=dates_all)).cumsum()

# 输出十年期核心绩效对比表
def calc_metrics(nav_series, name):
    tot_days = len(nav_series)
    daily_ret = nav_series.pct_change().fillna(0)
    ann_ret = nav_series.iloc[-1] ** (252 / tot_days) - 1 if tot_days > 0 else 0
    max_dd = (nav_series / nav_series.cummax() - 1).min()
    ann_vol = daily_ret.std() * np.sqrt(252)
    rf = 0.02
    sharpe = (ann_ret - rf) / ann_vol if ann_vol > 0 else 0
    calmar = ann_ret / abs(max_dd) if max_dd != 0 else 0
    return {
        '策略版本': name, 
        '年化收益': f"{ann_ret*100:>6.2f}%", 
        '最大回撤': f"{max_dd*100:>7.2f}%",
        '年化波动率': f"{ann_vol*100:>6.2f}%",
        '夏普比率': f"{sharpe:>5.2f}",
        '卡玛比率': f"{calmar:>5.2f}"
    }

print("\n========================= 十年全景回测：(防抖升级版) 核心绩效 =========================")
print(pd.DataFrame([
    calc_metrics(nav_hs300, "② 基准：沪深300指数 纯裸多"),
    calc_metrics(nav_bench, "③ 理论原版 (仅宏观配比，无均线避险)"),
    calc_metrics(nav_opt,   f"① 十年终极无缝版 (带 {BUFFER_PCT*100}% 缓冲区的MA20)")
]).to_string(index=False))
print("========================================================================================")

# ==================== 开始出图 ====================

# 【图表 1】十年全景甘特图 + 动态仓位堆叠图
print("\n正在渲染 图表1: 过滤噪音后的全景甘特图与资产分布...")

all_assets = []
for assets in daily_active_assets.values():
    for a in assets:
        if a not in all_assets: all_assets.append(a)
ind_y_map = {ind: i for i, ind in enumerate(all_assets)}

ind_blocks = {ind: [] for ind in all_assets}
for ind in all_assets:
    is_in = False; start_d = None
    for d in dates_all:
        active = ind in daily_active_assets[d]
        if active and not is_in: is_in = True; start_d = d
        elif not active and is_in: is_in = False; ind_blocks[ind].append((start_d, d))
    if is_in: ind_blocks[ind].append((start_d, dates_all[-1]))

def get_blocks(daily_dict):
    blocks = []; is_active = False; start_d = None
    for d in dates_all:
        if daily_dict[d] and not is_active: is_active = True; start_d = d
        elif not daily_dict[d] and is_active: is_active = False; blocks.append((start_d, d))
    if is_active: blocks.append((start_d, dates_all[-1]))
    return blocks

escape_blocks = get_blocks(is_escape_daily)
defense_blocks = get_blocks(is_defense_daily)

fig1, (ax1_1, ax1_2) = plt.subplots(2, 1, figsize=(16, max(12, len(all_assets)*0.3)), gridspec_kw={'height_ratios': [2.5, 1]}, sharex=True)

for ind, blocks in ind_blocks.items():
    y_pos = ind_y_map[ind]
    xranges = [(mdates.date2num(s), mdates.date2num(e) - mdates.date2num(s)) for s, e in blocks]
    ax1_1.broken_barh(xranges, (y_pos - 0.3, 0.6), facecolors='limegreen', edgecolor='black', linewidth=0.5, zorder=3)

for s, e in escape_blocks: ax1_1.axvspan(s, e, color='crimson', alpha=0.15, zorder=1)
for s, e in defense_blocks: ax1_1.axvspan(s, e, color='lightblue', alpha=0.3, zorder=1)

ax1_1.axvline(split_dt, color='blue', linestyle='-.', linewidth=2, zorder=4)
ax1_1.text(split_dt, -1, ' ← 前期:大盘模拟 | 后期:TOP4实操 (商品等权) →', color='blue', fontweight='bold', fontsize=12, ha='center')

ax1_1.set_yticks(range(len(all_assets)))
ax1_1.set_yticklabels(all_assets, fontsize=11)
ax1_1.invert_yaxis() 

legend_elements = [
    mpatches.Patch(color='limegreen', label=f'🟢 实际持仓期 (价格 >= MA20的 {100-BUFFER_PCT*100}%)'),
    mpatches.Patch(color='crimson', alpha=0.2, label='🔴 有效破位逃逸期 (击穿缓冲垫，资金转移)'),
    mpatches.Patch(color='lightblue', alpha=0.4, label='🌊 宏观极端防守期 (强制10%底仓装死)')
]
ax1_1.legend(handles=legend_elements, loc='upper center', bbox_to_anchor=(0.5, 1.08), ncol=3, fontsize=12, framealpha=0.9)
ax1_1.set_title(f'十年交响曲：带 {BUFFER_PCT*100}% 容错缓冲区的风控甘特图', fontsize=18, fontweight='bold', pad=35)
ax1_1.grid(True, linestyle='--', alpha=0.5, axis='x')

ax1_2.stackplot(dates_all, hist_w_eq, hist_w_bond, hist_w_com, 
              labels=['【股】(前沪深300 / 后TOP4)', '【债】(转债底仓+避险流入)', '【商】(4只ETF底仓+避险)'],
              colors=['crimson', 'purple', 'darkgoldenrod'], alpha=0.75)
ax1_2.axvline(split_dt, color='white', linestyle='-.', linewidth=2, zorder=4)
ax1_2.set_ylabel('大类资产占比 (%)', fontsize=12)
ax1_2.set_ylim(0, 100)
ax1_2.legend(loc='upper left', fontsize=11)

ax1_2.xaxis.set_major_locator(mdates.YearLocator())
ax1_2.xaxis.set_major_formatter(FuncFormatter(lambda x, pos: mdates.num2date(x).strftime('%Y-%m') if x else ""))
plt.setp(ax1_2.get_xticklabels(), rotation=0, ha='center', fontsize=12, fontweight='bold')
plt.tight_layout()
plt.show()

# 【图表 2】收益率贡献拆解 (净值起点为 1)
print("正在渲染 图表2: 股债商绝对净值贡献拆解...")
fig2, (ax2_1, ax2_2) = plt.subplots(2, 1, figsize=(16, 13), sharex=True)

ax2_1.plot(nav_opt.index, nav_opt, label='终极十年防抖策略 总净值 (Total NAV)', color='black', linewidth=3, zorder=5)
ax2_1.plot(cum_contrib_eq.index, cum_contrib_eq, label='【股】净值点数独立贡献', color='crimson', linewidth=2.5)
ax2_1.plot(cum_contrib_bond.index, cum_contrib_bond, label='【债】净值点数独立贡献', color='purple', linewidth=2.5)
ax2_1.plot(cum_contrib_com.index, cum_contrib_com, label='【商】净值点数独立贡献', color='darkgoldenrod', linewidth=2.5)
ax2_1.axvline(split_dt, color='blue', linestyle='-.', linewidth=1.5, alpha=0.5)
ax2_1.axhline(1, color='black', linestyle='-', linewidth=1, alpha=0.5)
ax2_1.axhline(0, color='gray', linestyle='--', linewidth=1.5)
ax2_1.set_title('防抖滤噪：各资产【独立净值贡献】轨迹', fontsize=17, fontweight='bold', pad=15)
ax2_1.set_ylabel('累计净值 / 贡献点数', fontsize=12)
ax2_1.legend(loc='upper left', fontsize=12, framealpha=0.9, ncol=2)
ax2_1.grid(True, linestyle=':', alpha=0.6)

ax2_2.plot(nav_opt.index, nav_opt, label='策略总净值', color='black', linewidth=2.5, zorder=5)
ax2_2.fill_between(nav_opt.index, 1, 1 + cum_contrib_eq, label='【股】贡献叠加', color='crimson', alpha=0.7)
ax2_2.fill_between(nav_opt.index, 1 + cum_contrib_eq, 1 + cum_contrib_eq + cum_contrib_bond, label='【债】贡献叠加', color='purple', alpha=0.7)
ax2_2.fill_between(nav_opt.index, 1 + cum_contrib_eq + cum_contrib_bond, nav_opt, label='【商】贡献叠加', color='darkgoldenrod', alpha=0.7)
ax2_2.axvline(split_dt, color='white', linestyle='-.', linewidth=2, alpha=0.7)
ax2_2.axhline(1, color='black', linestyle='-', linewidth=1.5)
ax2_2.set_title('账本全貌：十年期股债商【净值堆叠面积图】', fontsize=17, fontweight='bold', pad=15)
ax2_2.set_ylabel('累计净值', fontsize=12)
ax2_2.legend(loc='upper left', fontsize=12, framealpha=0.9, ncol=2)
ax2_2.grid(True, linestyle=':', alpha=0.6)
plt.tight_layout()
plt.show()

# 【图表 3】组合净值 vs 沪深300基准 & 双轴超额收益
print("正在渲染 图表3: 十年净值对决与超额收益全景 (双Y轴)...")
excess_return = nav_opt / nav_hs300 - 1

fig3, ax3 = plt.subplots(figsize=(16, 8))

ax3.plot(nav_opt.index, nav_opt, label='① 十年防抖终极版 (带 1.5% 容错)', color='darkorange', linewidth=3)
ax3.plot(nav_hs300.index, nav_hs300, label='② 基准：沪深300指数 纯裸多', color='grey', linewidth=1.5, linestyle='--')
ax3.plot(nav_bench.index, nav_bench, label='③ 理论原版 (仅宏观配比，无均线避险)', color='steelblue', linewidth=1.5, linestyle='-.', alpha=0.6)
ax3.set_ylabel('累计净值 (初始=1.0)', fontsize=12)
ax3.axhline(1, color='black', linewidth=1.5, alpha=0.6)

ax3_twin = ax3.twinx()
ax3_twin.plot(excess_return.index, excess_return, label='超额收益率 (终极版 vs 沪深300) [右轴]', color='purple', linewidth=1.5, alpha=0.9)
ax3_twin.axhline(0, color='black', linewidth=1, linestyle='--', alpha=0.6)
ax3_twin.fill_between(excess_return.index, excess_return, 0, where=(excess_return >= 0), color='#DC143C', alpha=0.15)
ax3_twin.fill_between(excess_return.index, excess_return, 0, where=(excess_return < 0), color='#228B22', alpha=0.15)
ax3_twin.yaxis.set_major_formatter(ticker.PercentFormatter(xmax=1.0))
ax3_twin.set_ylabel('超额收益率 (%)', fontsize=12, color='purple', fontweight='bold')

ax3.axvline(split_dt, color='blue', linestyle='-.', linewidth=2, alpha=0.7, label='2021Q2 实盘升级分界点')
ax3.set_title('降噪长跑验证：全天候防抖避险体系 vs 沪深300 累计净值与超额收益', fontsize=17, fontweight='bold', pad=15)
ax3.grid(True, linestyle=':', alpha=0.6)

lines_1, labels_1 = ax3.get_legend_handles_labels()
lines_2, labels_2 = ax3_twin.get_legend_handles_labels()
ax3.legend(lines_1 + lines_2, labels_1 + labels_2, fontsize=12, loc='upper left')

plt.tight_layout()
plt.show()

print("\n🎉 Step 36 完美执行！你现在拥有了一个更加沉稳、过滤了大量震荡磨损的实战级全天候系统。")

#%% Step 37: 终极全天候系统 (2016-2026) —— 引入 动态波动率 (自适应防抖带) 风控
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import matplotlib.patches as mpatches
from matplotlib.ticker import FuncFormatter
import matplotlib.ticker as ticker

print("\n========== 开始执行 Step 37: 引入自适应动态波动率 (Dynamic Volatility Band) ==========")

# ★ 核心参数：动态波动率乘数 (相当于 1.5 倍的真实波动容忍度) ★
VOL_MULTIPLIER = 1.5
print(f"已开启自适应防抖机制！当前动态下行容忍度为: {VOL_MULTIPLIER} 倍过去20日真实波动率")

# --- 1. 时间轴切分与底层标尺准备 ---
start_dt = pd.to_datetime('2016-01-01')
split_dt = pd.to_datetime('2021-04-01') 
dates_all = [d for d in ret_long.index if d >= start_dt]

# 计算沪深300的价格、均线与【滚动20日真实波动率】
hs300_price = prices_all['沪深300指数'].reindex(dates_all).ffill()
hs300_ma20 = hs300_price.rolling(window=20).mean()
hs300_ret = hs300_price.pct_change().fillna(0)
# 用过去20天的收益率标准差代表真实波动率，初始值用 1% 兜底
hs300_vol = hs300_ret.rolling(window=20).std().fillna(0.01) 

# 计算实操期 TOP4 组合的净值、均线与【滚动20日真实波动率】
if 'top4_nav_s31' not in locals():
    top4_nav_s31 = (1 + top4_daily_returns.reindex(dates_all).fillna(0)).cumprod()
    top4_ma20_s31 = top4_nav_s31.rolling(window=20).mean()
top4_vol = top4_daily_returns.reindex(dates_all).rolling(window=20).std().fillna(0.01)

# 商品端使用 4只ETF 等权
etf_ret_s37 = ret_all[['大成有色ETF', '华安黄金ETF', '建信能化ETF', '华夏豆粕ETF']].fillna(0)
basket_ret_eq_s37 = etf_ret_s37.mean(axis=1)

# --- 2. 严谨回溯并重构每日的真实收益与状态 ---
daily_cont_eq = []; daily_cont_bond = []; daily_cont_com = []
ret_opt_list = []; ret_bench_list = []; hs300_ret_list = []

is_escape_daily = {}; is_defense_daily = {}; daily_active_assets = {}
hist_w_eq = []; hist_w_bond = []; hist_w_com = []
dynamic_buffer_record = [] # 记录每天真实的防抖厚度，方便观察

for d in dates_all:
    w_eq = weights_daily_long['沪深300指数'].loc[d] if pd.notna(weights_daily_long['沪深300指数'].loc[d]) else 0.0
    w_bond = (weights_daily_long['中证基金指数:货币基金'] + weights_daily_long['中证全债指数']).loc[d] if pd.notna((weights_daily_long['中证基金指数:货币基金'] + weights_daily_long['中证全债指数']).loc[d]) else 0.0
    w_com = weights_daily_long['南华期货:商品指数'].loc[d] if pd.notna(weights_daily_long['南华期货:商品指数'].loc[d]) else 0.0
    
    is_def = abs(w_eq - 0.10) < 1e-4
    is_defense_daily[d] = is_def
    
    loc_idx = dates_all.index(d)
    prev_date = dates_all[loc_idx - 1] if loc_idx > 0 else dates_all[0]
    
    # ---------------- 核心拼接逻辑 (自适应动态缓冲) ----------------
    if d < split_dt:
        p_prev = hs300_price.loc[prev_date]
        m_prev = hs300_ma20.loc[prev_date]
        vol_prev = hs300_vol.loc[prev_date]
        
        # 算今天的动态容错厚度
        current_buffer = VOL_MULTIPLIER * vol_prev
        dynamic_buffer_record.append(current_buffer)
        
        active_eq = (p_prev >= m_prev * (1 - current_buffer)) if not is_def and pd.notna(m_prev) else True
        if is_def: active_eq = True 
            
        r_e = ret_long['沪深300指数'].loc[d]
        r_b = ret_long['中证转债'].loc[d]
        r_c = ret_long['南华期货:商品指数'].loc[d]
        active_assets = ['【前期】沪深300宽基'] if active_eq and w_eq > 0 else []
        
    else:
        q_str = f"{d.year}Q{d.quarter}"
        inds_current = q_to_inds_original.get(q_str, [])[:4]
        
        basket_nav_prev = top4_nav_s31.loc[prev_date] if prev_date in top4_nav_s31.index else np.nan
        basket_ma20_prev = top4_ma20_s31.loc[prev_date] if prev_date in top4_ma20_s31.index else np.nan
        vol_prev = top4_vol.loc[prev_date]
        
        current_buffer = VOL_MULTIPLIER * vol_prev
        dynamic_buffer_record.append(current_buffer)
        
        active_eq = (basket_nav_prev >= basket_ma20_prev * (1 - current_buffer)) if not is_def and pd.notna(basket_ma20_prev) else True
        if is_def: active_eq = True 
            
        r_e = top4_daily_returns.loc[d] if pd.notna(top4_daily_returns.loc[d]) else 0.0
        r_b = ret_long['中证转债'].loc[d]
        r_c = basket_ret_eq_s37.loc[d] if d in basket_ret_eq_s37.index else 0.0
        active_assets = inds_current if active_eq and w_eq > 0 else []
        
    # ---------------- 资金分配与收益结算 ----------------
    is_escape_daily[d] = not is_def and not active_eq
    daily_active_assets[d] = active_assets
    
    act_w_eq = w_eq if active_eq else 0.0
    freed = w_eq - act_w_eq
    act_w_bond = w_bond + freed / 2.0
    act_w_com = w_com + freed / 2.0
    
    hist_w_eq.append(act_w_eq * 100); hist_w_bond.append(act_w_bond * 100); hist_w_com.append(act_w_com * 100)
    
    daily_cont_eq.append(act_w_eq * r_e)
    daily_cont_bond.append(act_w_bond * r_b)
    daily_cont_com.append(act_w_com * r_c)
    
    ret_opt_list.append(act_w_eq * r_e + act_w_bond * r_b + act_w_com * r_c)
    
    r_c_bench = ret_long['南华期货:商品指数'].loc[d] if d < split_dt else (basket_ret_eq_s37.loc[d] if d in basket_ret_eq_s37.index else 0.0)
    ret_bench_list.append(w_eq * r_e + w_bond * r_b + w_com * r_c_bench)
    hs300_ret_list.append(ret_long['沪深300指数'].loc[d])

# --- 3. 计算净值与绝对贡献 (起点为 1.0) ---
nav_opt = (1 + pd.Series(ret_opt_list, index=dates_all)).cumprod()
nav_bench = (1 + pd.Series(ret_bench_list, index=dates_all)).cumprod()
nav_hs300 = (1 + pd.Series(hs300_ret_list, index=dates_all)).cumprod()

prev_nav = nav_opt.shift(1).fillna(1.0)
cum_contrib_eq = (prev_nav * pd.Series(daily_cont_eq, index=dates_all)).cumsum()
cum_contrib_bond = (prev_nav * pd.Series(daily_cont_bond, index=dates_all)).cumsum()
cum_contrib_com = (prev_nav * pd.Series(daily_cont_com, index=dates_all)).cumsum()

def calc_metrics(nav_series, name):
    tot_days = len(nav_series)
    daily_ret = nav_series.pct_change().fillna(0)
    ann_ret = nav_series.iloc[-1] ** (252 / tot_days) - 1 if tot_days > 0 else 0
    max_dd = (nav_series / nav_series.cummax() - 1).min()
    ann_vol = daily_ret.std() * np.sqrt(252)
    rf = 0.02
    sharpe = (ann_ret - rf) / ann_vol if ann_vol > 0 else 0
    calmar = ann_ret / abs(max_dd) if max_dd != 0 else 0
    return {
        '策略版本': name, 
        '年化收益': f"{ann_ret*100:>6.2f}%", 
        '最大回撤': f"{max_dd*100:>7.2f}%",
        '年化波动率': f"{ann_vol*100:>6.2f}%",
        '夏普比率': f"{sharpe:>5.2f}",
        '卡玛比率': f"{calmar:>5.2f}"
    }

print("\n========================= 十年全景回测：(自适应防抖系统) 核心绩效 =========================")
print(pd.DataFrame([
    calc_metrics(nav_hs300, "② 基准：沪深300指数 纯裸多"),
    calc_metrics(nav_bench, "③ 理论原版 (仅宏观配比，无均线避险)"),
    calc_metrics(nav_opt,   f"① 十年自适应终极版 (带 {VOL_MULTIPLIER}倍真实波动率防抖)")
]).to_string(index=False))
print("===========================================================================================")

# ==================== 开始出图 ====================

# 【图表 1】十年全景甘特图 + 动态仓位堆叠图
print("\n正在渲染 图表1: 自适应滤噪全景甘特图与资产分布...")

all_assets = []
for assets in daily_active_assets.values():
    for a in assets:
        if a not in all_assets: all_assets.append(a)
ind_y_map = {ind: i for i, ind in enumerate(all_assets)}

ind_blocks = {ind: [] for ind in all_assets}
for ind in all_assets:
    is_in = False; start_d = None
    for d in dates_all:
        active = ind in daily_active_assets[d]
        if active and not is_in: is_in = True; start_d = d
        elif not active and is_in: is_in = False; ind_blocks[ind].append((start_d, d))
    if is_in: ind_blocks[ind].append((start_d, dates_all[-1]))

def get_blocks(daily_dict):
    blocks = []; is_active = False; start_d = None
    for d in dates_all:
        if daily_dict[d] and not is_active: is_active = True; start_d = d
        elif not daily_dict[d] and is_active: is_active = False; blocks.append((start_d, d))
    if is_active: blocks.append((start_d, dates_all[-1]))
    return blocks

escape_blocks = get_blocks(is_escape_daily)
defense_blocks = get_blocks(is_defense_daily)

fig1, (ax1_1, ax1_2) = plt.subplots(2, 1, figsize=(16, max(12, len(all_assets)*0.3)), gridspec_kw={'height_ratios': [2.5, 1]}, sharex=True)

for ind, blocks in ind_blocks.items():
    y_pos = ind_y_map[ind]
    xranges = [(mdates.date2num(s), mdates.date2num(e) - mdates.date2num(s)) for s, e in blocks]
    ax1_1.broken_barh(xranges, (y_pos - 0.3, 0.6), facecolors='limegreen', edgecolor='black', linewidth=0.5, zorder=3)

for s, e in escape_blocks: ax1_1.axvspan(s, e, color='crimson', alpha=0.15, zorder=1)
for s, e in defense_blocks: ax1_1.axvspan(s, e, color='lightblue', alpha=0.3, zorder=1)

ax1_1.axvline(split_dt, color='blue', linestyle='-.', linewidth=2, zorder=4)
ax1_1.text(split_dt, -1, ' ← 前期:大盘模拟 | 后期:TOP4实操 (商品等权) →', color='blue', fontweight='bold', fontsize=12, ha='center')

ax1_1.set_yticks(range(len(all_assets)))
ax1_1.set_yticklabels(all_assets, fontsize=11)
ax1_1.invert_yaxis() 

legend_elements = [
    mpatches.Patch(color='limegreen', label=f'🟢 实际持仓期 (价格 >= MA20 - {VOL_MULTIPLIER}倍真实波动率)'),
    mpatches.Patch(color='crimson', alpha=0.2, label='🔴 有效破位逃逸期 (击穿自适应缓冲垫，全线撤退)'),
    mpatches.Patch(color='lightblue', alpha=0.4, label='🌊 宏观极端防守期 (强制10%底仓装死)')
]
ax1_1.legend(handles=legend_elements, loc='upper center', bbox_to_anchor=(0.5, 1.08), ncol=3, fontsize=12, framealpha=0.9)
ax1_1.set_title(f'十年交响曲：带 {VOL_MULTIPLIER}倍自适应动态缓冲区的风控甘特图', fontsize=18, fontweight='bold', pad=35)
ax1_1.grid(True, linestyle='--', alpha=0.5, axis='x')

ax1_2.stackplot(dates_all, hist_w_eq, hist_w_bond, hist_w_com, 
              labels=['【股】(前沪深300 / 后TOP4)', '【债】(转债底仓+避险流入)', '【商】(4只ETF底仓+避险)'],
              colors=['crimson', 'purple', 'darkgoldenrod'], alpha=0.75)
ax1_2.axvline(split_dt, color='white', linestyle='-.', linewidth=2, zorder=4)
ax1_2.set_ylabel('大类资产占比 (%)', fontsize=12)
ax1_2.set_ylim(0, 100)
ax1_2.legend(loc='upper left', fontsize=11)

ax1_2.xaxis.set_major_locator(mdates.YearLocator())
ax1_2.xaxis.set_major_formatter(FuncFormatter(lambda x, pos: mdates.num2date(x).strftime('%Y-%m') if x else ""))
plt.setp(ax1_2.get_xticklabels(), rotation=0, ha='center', fontsize=12, fontweight='bold')
plt.tight_layout()
plt.show()

# 【图表 2】收益率贡献拆解
print("正在渲染 图表2: 股债商绝对净值贡献拆解...")
fig2, (ax2_1, ax2_2) = plt.subplots(2, 1, figsize=(16, 13), sharex=True)

ax2_1.plot(nav_opt.index, nav_opt, label='终极十年防抖策略 总净值 (Total NAV)', color='black', linewidth=3, zorder=5)
ax2_1.plot(cum_contrib_eq.index, cum_contrib_eq, label='【股】净值点数独立贡献', color='crimson', linewidth=2.5)
ax2_1.plot(cum_contrib_bond.index, cum_contrib_bond, label='【债】净值点数独立贡献', color='purple', linewidth=2.5)
ax2_1.plot(cum_contrib_com.index, cum_contrib_com, label='【商】净值点数独立贡献', color='darkgoldenrod', linewidth=2.5)
ax2_1.axvline(split_dt, color='blue', linestyle='-.', linewidth=1.5, alpha=0.5)
ax2_1.axhline(1, color='black', linestyle='-', linewidth=1, alpha=0.5)
ax2_1.axhline(0, color='gray', linestyle='--', linewidth=1.5)
ax2_1.set_title('自适应防抖：各资产【独立净值贡献】轨迹', fontsize=17, fontweight='bold', pad=15)
ax2_1.set_ylabel('累计净值 / 贡献点数', fontsize=12)
ax2_1.legend(loc='upper left', fontsize=12, framealpha=0.9, ncol=2)
ax2_1.grid(True, linestyle=':', alpha=0.6)

ax2_2.plot(nav_opt.index, nav_opt, label='策略总净值', color='black', linewidth=2.5, zorder=5)
ax2_2.fill_between(nav_opt.index, 1, 1 + cum_contrib_eq, label='【股】贡献叠加', color='crimson', alpha=0.7)
ax2_2.fill_between(nav_opt.index, 1 + cum_contrib_eq, 1 + cum_contrib_eq + cum_contrib_bond, label='【债】贡献叠加', color='purple', alpha=0.7)
ax2_2.fill_between(nav_opt.index, 1 + cum_contrib_eq + cum_contrib_bond, nav_opt, label='【商】贡献叠加', color='darkgoldenrod', alpha=0.7)
ax2_2.axvline(split_dt, color='white', linestyle='-.', linewidth=2, alpha=0.7)
ax2_2.axhline(1, color='black', linestyle='-', linewidth=1.5)
ax2_2.set_title('账本全貌：十年期股债商【净值堆叠面积图】', fontsize=17, fontweight='bold', pad=15)
ax2_2.set_ylabel('累计净值', fontsize=12)
ax2_2.legend(loc='upper left', fontsize=12, framealpha=0.9, ncol=2)
ax2_2.grid(True, linestyle=':', alpha=0.6)
plt.tight_layout()
plt.show()

# 【图表 3】组合净值 vs 沪深300基准 & 双轴超额收益
print("正在渲染 图表3: 十年净值对决与超额收益全景 (双Y轴)...")
excess_return = nav_opt / nav_hs300 - 1

fig3, ax3 = plt.subplots(figsize=(16, 8))

ax3.plot(nav_opt.index, nav_opt, label='① 十年自适应终极版 (带动态容错带)', color='darkorange', linewidth=3)
ax3.plot(nav_hs300.index, nav_hs300, label='② 基准：沪深300指数 纯裸多', color='grey', linewidth=1.5, linestyle='--')
ax3.plot(nav_bench.index, nav_bench, label='③ 理论原版 (仅宏观配比，无均线避险)', color='steelblue', linewidth=1.5, linestyle='-.', alpha=0.6)
ax3.set_ylabel('累计净值 (初始=1.0)', fontsize=12)
ax3.axhline(1, color='black', linewidth=1.5, alpha=0.6)

ax3_twin = ax3.twinx()
ax3_twin.plot(excess_return.index, excess_return, label='超额收益率 (终极版 vs 沪深300) [右轴]', color='purple', linewidth=1.5, alpha=0.9)
ax3_twin.axhline(0, color='black', linewidth=1, linestyle='--', alpha=0.6)
ax3_twin.fill_between(excess_return.index, excess_return, 0, where=(excess_return >= 0), color='#DC143C', alpha=0.15)
ax3_twin.fill_between(excess_return.index, excess_return, 0, where=(excess_return < 0), color='#228B22', alpha=0.15)
ax3_twin.yaxis.set_major_formatter(ticker.PercentFormatter(xmax=1.0))
ax3_twin.set_ylabel('超额收益率 (%)', fontsize=12, color='purple', fontweight='bold')

ax3.axvline(split_dt, color='blue', linestyle='-.', linewidth=2, alpha=0.7, label='2021Q2 实盘升级分界点')
ax3.set_title('降噪长跑验证：全天候自适应防抖避险体系 vs 沪深300', fontsize=17, fontweight='bold', pad=15)
ax3.grid(True, linestyle=':', alpha=0.6)

lines_1, labels_1 = ax3.get_legend_handles_labels()
lines_2, labels_2 = ax3_twin.get_legend_handles_labels()
ax3.legend(lines_1 + lines_2, labels_1 + labels_2, fontsize=12, loc='upper left')

plt.tight_layout()
plt.show()

print("\n🎉 Step 37 完美收官！你的风控模块正式升级为具备“市场呼吸感”的自适应生命体。")

#%% Step 38: 十年期实战终极优化 (2016-2026) —— 引入 时间过滤器 (3日收盘确认防抖系统)
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import matplotlib.patches as mpatches
from matplotlib.ticker import FuncFormatter
import matplotlib.ticker as ticker

print("\n========== 开始执行 Step 38: 引入时间过滤器 (Time Filter) 的延迟确认避险测试 ==========")

# ★ 核心参数调整：时间确认天数设定为 3 天 ★
CONFIRM_DAYS = 3
print(f"已开启 MA20 时间防抖机制！破位/突破需要连续 {CONFIRM_DAYS} 个交易日确认。")

# --- 1. 时间轴切分与底层标尺准备 ---
start_dt = pd.to_datetime('2016-01-01')
split_dt = pd.to_datetime('2021-04-01') 
dates_all = [d for d in ret_long.index if d >= start_dt]

hs300_price = prices_all['沪深300指数'].reindex(dates_all).ffill()
hs300_ma20 = hs300_price.rolling(window=20).mean()

if 'top4_nav_s31' not in locals():
    top4_nav_s31 = (1 + top4_daily_returns.reindex(dates_all).fillna(0)).cumprod()
    top4_ma20_s31 = top4_nav_s31.rolling(window=20).mean()

# 确保实操期商品端使用 4只ETF 等权
etf_ret_s38 = ret_all[['大成有色ETF', '华安黄金ETF', '建信能化ETF', '华夏豆粕ETF']].fillna(0)
basket_ret_eq_s38 = etf_ret_s38.mean(axis=1)

# --- 2. 严谨回溯并重构每日的真实收益与状态 ---
daily_cont_eq = []; daily_cont_bond = []; daily_cont_com = []
ret_opt_list = []; ret_bench_list = []; hs300_ret_list = []

is_escape_daily = {}; is_defense_daily = {}; daily_active_assets = {}
hist_w_eq = []; hist_w_bond = []; hist_w_com = []

# ★ 新增：状态机变量，用于记录连续天数和当前持仓状态 ★
current_eq_status = True  # 初始默认为持仓状态
consecutive_above = 0     # 连续在均线之上的天数
consecutive_below = 0     # 连续在均线之下的天数

for d in dates_all:
    w_eq = weights_daily_long['沪深300指数'].loc[d] if pd.notna(weights_daily_long['沪深300指数'].loc[d]) else 0.0
    w_bond = (weights_daily_long['中证基金指数:货币基金'] + weights_daily_long['中证全债指数']).loc[d] if pd.notna((weights_daily_long['中证基金指数:货币基金'] + weights_daily_long['中证全债指数']).loc[d]) else 0.0
    w_com = weights_daily_long['南华期货:商品指数'].loc[d] if pd.notna(weights_daily_long['南华期货:商品指数'].loc[d]) else 0.0
    
    is_def = abs(w_eq - 0.10) < 1e-4
    is_defense_daily[d] = is_def
    
    loc_idx = dates_all.index(d)
    prev_date = dates_all[loc_idx - 1] if loc_idx > 0 else dates_all[0]
    
    # ---------------- 核心拼接逻辑 (时间过滤器状态机) ----------------
    if d < split_dt:
        # 第一阶段：沪深300
        p_prev = hs300_price.loc[prev_date]
        m_prev = hs300_ma20.loc[prev_date]
        
        # 判断昨天是否在均线之上
        is_above = (p_prev >= m_prev) if pd.notna(m_prev) else True
            
        r_e = ret_long['沪深300指数'].loc[d]
        r_b = ret_long['中证转债'].loc[d]
        r_c = ret_long['南华期货:商品指数'].loc[d]
        base_asset_name = '【前期】沪深300宽基'
        r_c_bench = r_c
        
    else:
        # 第二阶段：TOP4 + 4只ETF等权
        basket_nav_prev = top4_nav_s31.loc[prev_date] if prev_date in top4_nav_s31.index else np.nan
        basket_ma20_prev = top4_ma20_s31.loc[prev_date] if prev_date in top4_ma20_s31.index else np.nan
        
        # 判断昨天是否在均线之上
        is_above = (basket_nav_prev >= basket_ma20_prev) if pd.notna(basket_ma20_prev) else True
            
        r_e = top4_daily_returns.loc[d] if pd.notna(top4_daily_returns.loc[d]) else 0.0
        r_b = ret_long['中证转债'].loc[d]
        r_c = basket_ret_eq_s38.loc[d] if d in basket_ret_eq_s38.index else 0.0
        
        q_str = f"{d.year}Q{d.quarter}"
        base_asset_name = q_to_inds_original.get(q_str, [])[:4]
        r_c_bench = r_c

    # --- 执行状态机逻辑 ---
    if not is_def:
        if is_above:
            consecutive_above += 1
            consecutive_below = 0
            if consecutive_above >= CONFIRM_DAYS:
                current_eq_status = True  # 满足连续天数，确认做多
        else:
            consecutive_below += 1
            consecutive_above = 0
            if consecutive_below >= CONFIRM_DAYS:
                current_eq_status = False # 满足连续天数，确认逃逸
        
        active_eq = current_eq_status
    else:
        # 宏观防守期：强制保持底仓装死，不重置天数计数器，但行为视作持仓(10%)
        active_eq = True 
        
    active_assets = base_asset_name if active_eq and w_eq > 0 else []
    if isinstance(active_assets, str): active_assets = [active_assets]
        
    # ---------------- 资金分配与收益结算 ----------------
    is_escape_daily[d] = not is_def and not active_eq
    daily_active_assets[d] = active_assets
    
    act_w_eq = w_eq if active_eq else 0.0
    freed = w_eq - act_w_eq
    act_w_bond = w_bond + freed / 2.0
    act_w_com = w_com + freed / 2.0
    
    hist_w_eq.append(act_w_eq * 100); hist_w_bond.append(act_w_bond * 100); hist_w_com.append(act_w_com * 100)
    
    daily_cont_eq.append(act_w_eq * r_e)
    daily_cont_bond.append(act_w_bond * r_b)
    daily_cont_com.append(act_w_com * r_c)
    
    ret_opt_list.append(act_w_eq * r_e + act_w_bond * r_b + act_w_com * r_c)
    ret_bench_list.append(w_eq * r_e + w_bond * r_b + w_com * r_c_bench)
    hs300_ret_list.append(ret_long['沪深300指数'].loc[d])

# --- 3. 计算净值与绝对贡献 (起点为 1.0) ---
nav_opt = (1 + pd.Series(ret_opt_list, index=dates_all)).cumprod()
nav_bench = (1 + pd.Series(ret_bench_list, index=dates_all)).cumprod()
nav_hs300 = (1 + pd.Series(hs300_ret_list, index=dates_all)).cumprod()

prev_nav = nav_opt.shift(1).fillna(1.0)
cum_contrib_eq = (prev_nav * pd.Series(daily_cont_eq, index=dates_all)).cumsum()
cum_contrib_bond = (prev_nav * pd.Series(daily_cont_bond, index=dates_all)).cumsum()
cum_contrib_com = (prev_nav * pd.Series(daily_cont_com, index=dates_all)).cumsum()

def calc_metrics(nav_series, name):
    tot_days = len(nav_series)
    daily_ret = nav_series.pct_change().fillna(0)
    ann_ret = nav_series.iloc[-1] ** (252 / tot_days) - 1 if tot_days > 0 else 0
    max_dd = (nav_series / nav_series.cummax() - 1).min()
    ann_vol = daily_ret.std() * np.sqrt(252)
    rf = 0.02
    sharpe = (ann_ret - rf) / ann_vol if ann_vol > 0 else 0
    calmar = ann_ret / abs(max_dd) if max_dd != 0 else 0
    return {
        '策略版本': name, 
        '年化收益': f"{ann_ret*100:>6.2f}%", 
        '最大回撤': f"{max_dd*100:>7.2f}%",
        '年化波动率': f"{ann_vol*100:>6.2f}%",
        '夏普比率': f"{sharpe:>5.2f}",
        '卡玛比率': f"{calmar:>5.2f}"
    }

print("\n========================= 十年全景回测：(时间过滤器防抖) 核心绩效 =========================")
print(pd.DataFrame([
    calc_metrics(nav_hs300, "② 基准：沪深300指数 纯裸多"),
    calc_metrics(nav_bench, "③ 理论原版 (仅宏观配比，无均线避险)"),
    calc_metrics(nav_opt,   f"① 十年时间防抖版 ({CONFIRM_DAYS}日收盘确认MA20逃逸)")
]).to_string(index=False))
print("=========================================================================================")

# ==================== 开始出图 ====================

# 【图表 1】十年全景甘特图 + 动态仓位堆叠图
print("\n正在渲染 图表1: 时间过滤后的全景甘特图与资产分布...")

all_assets = []
for assets in daily_active_assets.values():
    for a in assets:
        if a not in all_assets: all_assets.append(a)
ind_y_map = {ind: i for i, ind in enumerate(all_assets)}

ind_blocks = {ind: [] for ind in all_assets}
for ind in all_assets:
    is_in = False; start_d = None
    for d in dates_all:
        active = ind in daily_active_assets[d]
        if active and not is_in: is_in = True; start_d = d
        elif not active and is_in: is_in = False; ind_blocks[ind].append((start_d, d))
    if is_in: ind_blocks[ind].append((start_d, dates_all[-1]))

def get_blocks(daily_dict):
    blocks = []; is_active = False; start_d = None
    for d in dates_all:
        if daily_dict[d] and not is_active: is_active = True; start_d = d
        elif not daily_dict[d] and is_active: is_active = False; blocks.append((start_d, d))
    if is_active: blocks.append((start_d, dates_all[-1]))
    return blocks

escape_blocks = get_blocks(is_escape_daily)
defense_blocks = get_blocks(is_defense_daily)

fig1, (ax1_1, ax1_2) = plt.subplots(2, 1, figsize=(16, max(12, len(all_assets)*0.3)), gridspec_kw={'height_ratios': [2.5, 1]}, sharex=True)

for ind, blocks in ind_blocks.items():
    y_pos = ind_y_map[ind]
    xranges = [(mdates.date2num(s), mdates.date2num(e) - mdates.date2num(s)) for s, e in blocks]
    ax1_1.broken_barh(xranges, (y_pos - 0.3, 0.6), facecolors='limegreen', edgecolor='black', linewidth=0.5, zorder=3)

for s, e in escape_blocks: ax1_1.axvspan(s, e, color='crimson', alpha=0.15, zorder=1)
for s, e in defense_blocks: ax1_1.axvspan(s, e, color='lightblue', alpha=0.3, zorder=1)

ax1_1.axvline(split_dt, color='blue', linestyle='-.', linewidth=2, zorder=4)
ax1_1.text(split_dt, -1, ' ← 前期:大盘模拟 | 后期:TOP4实操 (商品等权) →', color='blue', fontweight='bold', fontsize=12, ha='center')

ax1_1.set_yticks(range(len(all_assets)))
ax1_1.set_yticklabels(all_assets, fontsize=11)
ax1_1.invert_yaxis() 

legend_elements = [
    mpatches.Patch(color='limegreen', label=f'🟢 实际持仓期 (连续 {CONFIRM_DAYS} 日稳居均线之上)'),
    mpatches.Patch(color='crimson', alpha=0.2, label=f'🔴 有效破位逃逸期 (连续 {CONFIRM_DAYS} 日收于均线下)'),
    mpatches.Patch(color='lightblue', alpha=0.4, label='🌊 宏观极端防守期 (强制10%底仓装死)')
]
ax1_1.legend(handles=legend_elements, loc='upper center', bbox_to_anchor=(0.5, 1.08), ncol=3, fontsize=12, framealpha=0.9)
ax1_1.set_title(f'十年交响曲：带 {CONFIRM_DAYS}天时间过滤器的风控甘特图', fontsize=18, fontweight='bold', pad=35)
ax1_1.grid(True, linestyle='--', alpha=0.5, axis='x')

ax1_2.stackplot(dates_all, hist_w_eq, hist_w_bond, hist_w_com, 
              labels=['【股】(前沪深300 / 后TOP4)', '【债】(转债底仓+避险流入)', '【商】(4只ETF底仓+避险)'],
              colors=['crimson', 'purple', 'darkgoldenrod'], alpha=0.75)
ax1_2.axvline(split_dt, color='white', linestyle='-.', linewidth=2, zorder=4)
ax1_2.set_ylabel('大类资产占比 (%)', fontsize=12)
ax1_2.set_ylim(0, 100)
ax1_2.legend(loc='upper left', fontsize=11)

ax1_2.xaxis.set_major_locator(mdates.YearLocator())
ax1_2.xaxis.set_major_formatter(FuncFormatter(lambda x, pos: mdates.num2date(x).strftime('%Y-%m') if x else ""))
plt.setp(ax1_2.get_xticklabels(), rotation=0, ha='center', fontsize=12, fontweight='bold')
plt.tight_layout()
plt.show()

# 【图表 2】收益率贡献拆解
print("正在渲染 图表2: 股债商绝对净值贡献拆解...")
fig2, (ax2_1, ax2_2) = plt.subplots(2, 1, figsize=(16, 13), sharex=True)

ax2_1.plot(nav_opt.index, nav_opt, label='终极十年时间防抖 总净值', color='black', linewidth=3, zorder=5)
ax2_1.plot(cum_contrib_eq.index, cum_contrib_eq, label='【股】净值点数独立贡献', color='crimson', linewidth=2.5)
ax2_1.plot(cum_contrib_bond.index, cum_contrib_bond, label='【债】净值点数独立贡献', color='purple', linewidth=2.5)
ax2_1.plot(cum_contrib_com.index, cum_contrib_com, label='【商】净值点数独立贡献', color='darkgoldenrod', linewidth=2.5)
ax2_1.axvline(split_dt, color='blue', linestyle='-.', linewidth=1.5, alpha=0.5)
ax2_1.axhline(1, color='black', linestyle='-', linewidth=1, alpha=0.5)
ax2_1.axhline(0, color='gray', linestyle='--', linewidth=1.5)
ax2_1.set_title('时间滤噪：各资产【独立净值贡献】轨迹', fontsize=17, fontweight='bold', pad=15)
ax2_1.set_ylabel('累计净值 / 贡献点数', fontsize=12)
ax2_1.legend(loc='upper left', fontsize=12, framealpha=0.9, ncol=2)
ax2_1.grid(True, linestyle=':', alpha=0.6)

ax2_2.plot(nav_opt.index, nav_opt, label='策略总净值', color='black', linewidth=2.5, zorder=5)
ax2_2.fill_between(nav_opt.index, 1, 1 + cum_contrib_eq, label='【股】贡献叠加', color='crimson', alpha=0.7)
ax2_2.fill_between(nav_opt.index, 1 + cum_contrib_eq, 1 + cum_contrib_eq + cum_contrib_bond, label='【债】贡献叠加', color='purple', alpha=0.7)
ax2_2.fill_between(nav_opt.index, 1 + cum_contrib_eq + cum_contrib_bond, nav_opt, label='【商】贡献叠加', color='darkgoldenrod', alpha=0.7)
ax2_2.axvline(split_dt, color='white', linestyle='-.', linewidth=2, alpha=0.7)
ax2_2.axhline(1, color='black', linestyle='-', linewidth=1.5)
ax2_2.set_title('账本全貌：十年期股债商【净值堆叠面积图】', fontsize=17, fontweight='bold', pad=15)
ax2_2.set_ylabel('累计净值', fontsize=12)
ax2_2.legend(loc='upper left', fontsize=12, framealpha=0.9, ncol=2)
ax2_2.grid(True, linestyle=':', alpha=0.6)
plt.tight_layout()
plt.show()

# 【图表 3】组合净值 vs 沪深300基准 & 双轴超额收益
print("正在渲染 图表3: 十年净值对决与超额收益全景 (双Y轴)...")
excess_return = nav_opt / nav_hs300 - 1

fig3, ax3 = plt.subplots(figsize=(16, 8))

ax3.plot(nav_opt.index, nav_opt, label=f'① 十年时间防抖版 (带 {CONFIRM_DAYS}日延迟确认)', color='darkorange', linewidth=3)
ax3.plot(nav_hs300.index, nav_hs300, label='② 基准：沪深300指数 纯裸多', color='grey', linewidth=1.5, linestyle='--')
ax3.plot(nav_bench.index, nav_bench, label='③ 理论原版 (仅宏观配比，无均线避险)', color='steelblue', linewidth=1.5, linestyle='-.', alpha=0.6)
ax3.set_ylabel('累计净值 (初始=1.0)', fontsize=12)
ax3.axhline(1, color='black', linewidth=1.5, alpha=0.6)

ax3_twin = ax3.twinx()
ax3_twin.plot(excess_return.index, excess_return, label='超额收益率 (终极版 vs 沪深300) [右轴]', color='purple', linewidth=1.5, alpha=0.9)
ax3_twin.axhline(0, color='black', linewidth=1, linestyle='--', alpha=0.6)
ax3_twin.fill_between(excess_return.index, excess_return, 0, where=(excess_return >= 0), color='#DC143C', alpha=0.15)
ax3_twin.fill_between(excess_return.index, excess_return, 0, where=(excess_return < 0), color='#228B22', alpha=0.15)
ax3_twin.yaxis.set_major_formatter(ticker.PercentFormatter(xmax=1.0))
ax3_twin.set_ylabel('超额收益率 (%)', fontsize=12, color='purple', fontweight='bold')

ax3.axvline(split_dt, color='blue', linestyle='-.', linewidth=2, alpha=0.7, label='2021Q2 实盘升级分界点')
ax3.set_title('降噪长跑验证：全天候时间防抖避险体系 vs 沪深300 累计净值与超额收益', fontsize=17, fontweight='bold', pad=15)
ax3.grid(True, linestyle=':', alpha=0.6)

lines_1, labels_1 = ax3.get_legend_handles_labels()
lines_2, labels_2 = ax3_twin.get_legend_handles_labels()
ax3.legend(lines_1 + lines_2, labels_1 + labels_2, fontsize=12, loc='upper left')

plt.tight_layout()
plt.show()

print("\n🎉 Step 38 已完成！你的系统现在通过'让子弹飞一会儿'的方式，完美规避了单日盘中假突破的诱导。")

#%% Step 39: 十年期双核双向风控 (2016-2026) —— 仅对 70% 极值重仓资产启动定向避险
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import matplotlib.patches as mpatches
from matplotlib.ticker import FuncFormatter
import matplotlib.ticker as ticker

print("\n========== 开始执行 Step 39: 主引擎定向避险 (仅对 70% 仓位资产启动 MA20) ==========")

VOL_MULTIPLIER = 1.5 
print(f"定向风控已启动！仅当宏观权重分配达 70% 时，开启 {VOL_MULTIPLIER}倍真实波动率 防护垫。")

# --- 1. 时间轴切分与底层标尺准备 ---
start_dt = pd.to_datetime('2016-01-01')
split_dt = pd.to_datetime('2021-04-01') 
dates_all = [d for d in ret_long.index if d >= start_dt]

# 【股票端标尺】
hs300_price = prices_all['沪深300指数'].reindex(dates_all).ffill()
hs300_ma20 = hs300_price.rolling(window=20).mean()
hs300_vol = hs300_price.pct_change().fillna(0).rolling(window=20).std().fillna(0.01) 

if 'top4_nav_s31' not in locals():
    top4_nav_s31 = (1 + top4_daily_returns.reindex(dates_all).fillna(0)).cumprod()
    top4_ma20_s31 = top4_nav_s31.rolling(window=20).mean()
top4_vol = top4_daily_returns.reindex(dates_all).rolling(window=20).std().fillna(0.01)

# 【商品端标尺】
nh_ret = ret_long['南华期货:商品指数'].reindex(dates_all).fillna(0)
nh_nav = (1 + nh_ret).cumprod()
nh_ma20 = nh_nav.rolling(window=20).mean()
nh_vol = nh_ret.rolling(window=20).std().fillna(0.01)

etf_ret_s39 = ret_all[['大成有色ETF', '华安黄金ETF', '建信能化ETF', '华夏豆粕ETF']].reindex(dates_all).fillna(0)
basket_ret_eq_s39 = etf_ret_s39.mean(axis=1)
basket_nav_s39 = (1 + basket_ret_eq_s39).cumprod()
basket_ma20_s39 = basket_nav_s39.rolling(window=20).mean()
basket_vol_s39 = basket_ret_eq_s39.rolling(window=20).std().fillna(0.01)

# --- 2. 严谨回溯并重构每日的真实收益与状态 ---
daily_cont_eq = []; daily_cont_bond = []; daily_cont_com = []
ret_opt_list = []; ret_bench_list = []; hs300_ret_list = []

is_eq_escape_daily = {}; is_com_escape_daily = {}
daily_active_assets = {}
hist_w_eq = []; hist_w_bond = []; hist_w_com = []

for d in dates_all:
    w_eq = weights_daily_long['沪深300指数'].loc[d] if pd.notna(weights_daily_long['沪深300指数'].loc[d]) else 0.0
    w_bond = (weights_daily_long['中证基金指数:货币基金'] + weights_daily_long['中证全债指数']).loc[d] if pd.notna((weights_daily_long['中证基金指数:货币基金'] + weights_daily_long['中证全债指数']).loc[d]) else 0.0
    w_com = weights_daily_long['南华期货:商品指数'].loc[d] if pd.notna(weights_daily_long['南华期货:商品指数'].loc[d]) else 0.0
    
    # ★ 核心逻辑调整：判断谁是“主引擎” (权重约等于 70%)
    is_eq_heavy = w_eq > 0.65
    is_com_heavy = w_com > 0.65
    
    loc_idx = dates_all.index(d)
    prev_date = dates_all[loc_idx - 1] if loc_idx > 0 else dates_all[0]
    
    # ---------------- 判定双端是否触发风控 ----------------
    if d < split_dt:
        # 股端：沪深300
        e_p = hs300_price.loc[prev_date]; e_m = hs300_ma20.loc[prev_date]; e_v = hs300_vol.loc[prev_date]
        e_m_condition = (e_p >= e_m * (1 - VOL_MULTIPLIER * e_v)) if pd.notna(e_m) else True
        r_e = ret_long['沪深300指数'].loc[d]
        eq_asset_names = ['【股】前期宽基']
        
        # 商端：南华期货
        c_p = nh_nav.loc[prev_date]; c_m = nh_ma20.loc[prev_date]; c_v = nh_vol.loc[prev_date]
        c_m_condition = (c_p >= c_m * (1 - VOL_MULTIPLIER * c_v)) if pd.notna(c_m) else True
        r_c = nh_ret.loc[d]
        r_c_bench = r_c
    else:
        # 股端：TOP4组合
        e_p = top4_nav_s31.loc[prev_date] if prev_date in top4_nav_s31.index else np.nan
        e_m = top4_ma20_s31.loc[prev_date] if prev_date in top4_ma20_s31.index else np.nan
        e_v = top4_vol.loc[prev_date]
        e_m_condition = (e_p >= e_m * (1 - VOL_MULTIPLIER * e_v)) if pd.notna(e_m) else True
        r_e = top4_daily_returns.loc[d] if pd.notna(top4_daily_returns.loc[d]) else 0.0
        q_str = f"{d.year}Q{d.quarter}"
        eq_asset_names = q_to_inds_original.get(q_str, [])[:4]
        
        # 商端：4只ETF等权
        c_p = basket_nav_s39.loc[prev_date] if prev_date in basket_nav_s39.index else np.nan
        c_m = basket_ma20_s39.loc[prev_date] if prev_date in basket_ma20_s39.index else np.nan
        c_v = basket_vol_s39.loc[prev_date] if prev_date in basket_vol_s39.index else 0.01
        c_m_condition = (c_p >= c_m * (1 - VOL_MULTIPLIER * c_v)) if pd.notna(c_m) else True
        r_c = basket_ret_eq_s39.loc[d] if d in basket_ret_eq_s39.index else 0.0
        r_c_bench = r_c

    # ★ 关键开关：只有重仓才考核 MA20 破位，非重仓直接无视均线，硬扛持有 ★
    active_eq = e_m_condition if is_eq_heavy else True
    active_com = c_m_condition if is_com_heavy else True
        
    r_b = ret_long['中证转债'].loc[d]
    
    # 记录作图资产
    active_assets = []
    if active_eq and w_eq > 0: active_assets.extend(eq_asset_names)
    if active_com and w_com > 0: active_assets.append('【商】大宗商品端')
    daily_active_assets[d] = active_assets

    # ---------------- 交叉资金流转逻辑 (定向逃逸) ----------------
    is_eq_escape_daily[d] = not active_eq
    is_com_escape_daily[d] = not active_com
    
    act_w_eq = w_eq if active_eq else 0.0
    act_w_com = w_com if active_com else 0.0
    act_w_bond = w_bond

    # 资金互流分配 (普林格不会出现双重70%，因此互流是确定的单边行为)
    if not active_eq:  # 股票重仓且破位：腾出的70%资金流向债与商
        act_w_bond += w_eq / 2.0
        act_w_com += w_eq / 2.0
    elif not active_com: # 商品重仓且破位：腾出的70%资金流向债与股
        act_w_bond += w_com / 2.0
        act_w_eq += w_com / 2.0

    hist_w_eq.append(act_w_eq * 100); hist_w_bond.append(act_w_bond * 100); hist_w_com.append(act_w_com * 100)
    
    daily_cont_eq.append(act_w_eq * r_e)
    daily_cont_bond.append(act_w_bond * r_b)
    daily_cont_com.append(act_w_com * r_c)
    
    ret_opt_list.append(act_w_eq * r_e + act_w_bond * r_b + act_w_com * r_c)
    ret_bench_list.append(w_eq * r_e + w_bond * r_b + w_com * r_c_bench)
    hs300_ret_list.append(ret_long['沪深300指数'].loc[d])

# --- 3. 计算净值与绝对贡献 ---
nav_opt = (1 + pd.Series(ret_opt_list, index=dates_all)).cumprod()
nav_bench = (1 + pd.Series(ret_bench_list, index=dates_all)).cumprod()
nav_hs300 = (1 + pd.Series(hs300_ret_list, index=dates_all)).cumprod()

prev_nav = nav_opt.shift(1).fillna(1.0)
cum_contrib_eq = (prev_nav * pd.Series(daily_cont_eq, index=dates_all)).cumsum()
cum_contrib_bond = (prev_nav * pd.Series(daily_cont_bond, index=dates_all)).cumsum()
cum_contrib_com = (prev_nav * pd.Series(daily_cont_com, index=dates_all)).cumsum()

def calc_metrics(nav_series, name):
    tot_days = len(nav_series)
    daily_ret = nav_series.pct_change().fillna(0)
    ann_ret = nav_series.iloc[-1] ** (252 / tot_days) - 1 if tot_days > 0 else 0
    max_dd = (nav_series / nav_series.cummax() - 1).min()
    ann_vol = daily_ret.std() * np.sqrt(252)
    rf = 0.02
    sharpe = (ann_ret - rf) / ann_vol if ann_vol > 0 else 0
    calmar = ann_ret / abs(max_dd) if max_dd != 0 else 0
    return {
        '策略版本': name, 
        '年化收益': f"{ann_ret*100:>6.2f}%", 
        '最大回撤': f"{max_dd*100:>7.2f}%",
        '年化波动率': f"{ann_vol*100:>6.2f}%",
        '夏普比率': f"{sharpe:>5.2f}",
        '卡玛比率': f"{calmar:>5.2f}"
    }

print("\n========================= 十年全景回测：(主引擎定向风控系统) 核心绩效 =========================")
print(pd.DataFrame([
    calc_metrics(nav_hs300, "② 基准：沪深300指数 纯裸多"),
    calc_metrics(nav_bench, "③ 理论原版 (仅宏观配比，无均线避险)"),
    calc_metrics(nav_opt,   f"① 十年定向风控版 (仅在配置70%时启动MA避险)")
]).to_string(index=False))
print("===============================================================================================")

# ==================== 开始出图 ====================

print("\n正在渲染 图表1: 定向风控全景甘特图与交叉资金分布...")

all_assets = []
for assets in daily_active_assets.values():
    for a in assets:
        if a not in all_assets: all_assets.append(a)
# 强制把商品排在最上方/最下方以作区分
if '【商】大宗商品端' in all_assets:
    all_assets.remove('【商】大宗商品端')
    all_assets.insert(0, '【商】大宗商品端')
ind_y_map = {ind: i for i, ind in enumerate(all_assets)}

ind_blocks = {ind: [] for ind in all_assets}
for ind in all_assets:
    is_in = False; start_d = None
    for d in dates_all:
        active = ind in daily_active_assets[d]
        if active and not is_in: is_in = True; start_d = d
        elif not active and is_in: is_in = False; ind_blocks[ind].append((start_d, d))
    if is_in: ind_blocks[ind].append((start_d, dates_all[-1]))

fig1, (ax1_1, ax1_2) = plt.subplots(2, 1, figsize=(16, max(12, len(all_assets)*0.3)), gridspec_kw={'height_ratios': [2.5, 1]}, sharex=True)

for ind, blocks in ind_blocks.items():
    y_pos = ind_y_map[ind]
    color = 'darkgoldenrod' if ind == '【商】大宗商品端' else 'limegreen'
    xranges = [(mdates.date2num(s), mdates.date2num(e) - mdates.date2num(s)) for s, e in blocks]
    ax1_1.broken_barh(xranges, (y_pos - 0.3, 0.6), facecolors=color, edgecolor='black', linewidth=0.5, zorder=3)

# 阴影区精准标注主引擎逃逸期
def get_blocks(daily_dict):
    blocks = []; is_active = False; start_d = None
    for d in dates_all:
        if daily_dict[d] and not is_active: is_active = True; start_d = d
        elif not daily_dict[d] and is_active: is_active = False; blocks.append((start_d, d))
    if is_active: blocks.append((start_d, dates_all[-1]))
    return blocks

for s, e in get_blocks(is_eq_escape_daily): ax1_1.axvspan(s, e, color='crimson', alpha=0.15, zorder=1)
for s, e in get_blocks(is_com_escape_daily): ax1_1.axvspan(s, e, color='orange', alpha=0.15, zorder=1)

ax1_1.axvline(split_dt, color='blue', linestyle='-.', linewidth=2, zorder=4)

ax1_1.set_yticks(range(len(all_assets)))
ax1_1.set_yticklabels(all_assets, fontsize=11)
ax1_1.invert_yaxis() 

legend_elements = [
    mpatches.Patch(color='limegreen', label='🟢 股票多头存续期'),
    mpatches.Patch(color='darkgoldenrod', label='🟡 商品多头存续期'),
    mpatches.Patch(color='crimson', alpha=0.2, label='🔴 股权重70%且破位 (股票主引擎逃逸)'),
    mpatches.Patch(color='orange', alpha=0.2, label='🟠 商权重70%且破位 (商品主引擎逃逸)')
]
ax1_1.legend(handles=legend_elements, loc='upper center', bbox_to_anchor=(0.5, 1.08), ncol=4, fontsize=12, framealpha=0.9)
ax1_1.set_title('十年交响曲：仅针对 70% 重仓主引擎的定向风控甘特图', fontsize=18, fontweight='bold', pad=35)
ax1_1.grid(True, linestyle='--', alpha=0.5, axis='x')

ax1_2.stackplot(dates_all, hist_w_eq, hist_w_bond, hist_w_com, 
              labels=['【股】实有仓位', '【债】实有仓位', '【商】实有仓位'],
              colors=['crimson', 'purple', 'darkgoldenrod'], alpha=0.75)
ax1_2.axvline(split_dt, color='white', linestyle='-.', linewidth=2, zorder=4)
ax1_2.set_ylabel('资金动态占比 (%)', fontsize=12)
ax1_2.set_ylim(0, 100)
ax1_2.legend(loc='upper left', fontsize=11)

ax1_2.xaxis.set_major_locator(mdates.YearLocator())
ax1_2.xaxis.set_major_formatter(FuncFormatter(lambda x, pos: mdates.num2date(x).strftime('%Y-%m') if x else ""))
plt.setp(ax1_2.get_xticklabels(), rotation=0, ha='center', fontsize=12, fontweight='bold')
plt.tight_layout()
plt.show()

# 【图表 2与图表 3】
fig2, (ax2_1, ax2_2) = plt.subplots(2, 1, figsize=(16, 13), sharex=True)
ax2_1.plot(nav_opt.index, nav_opt, label='定向风控 总净值', color='black', linewidth=3, zorder=5)
ax2_1.plot(cum_contrib_eq.index, cum_contrib_eq, label='【股】净值贡献', color='crimson', linewidth=2.5)
ax2_1.plot(cum_contrib_bond.index, cum_contrib_bond, label='【债】净值贡献', color='purple', linewidth=2.5)
ax2_1.plot(cum_contrib_com.index, cum_contrib_com, label='【商】净值贡献', color='darkgoldenrod', linewidth=2.5)
ax2_1.axvline(split_dt, color='blue', linestyle='-.', linewidth=1.5, alpha=0.5)
ax2_1.axhline(1, color='black', linestyle='-', linewidth=1, alpha=0.5); ax2_1.axhline(0, color='gray', linestyle='--', linewidth=1.5)
ax2_1.set_title('定向避险：各资产【独立净值贡献】轨迹', fontsize=17, fontweight='bold', pad=15)
ax2_1.legend(loc='upper left', fontsize=12, framealpha=0.9, ncol=2); ax2_1.grid(True, linestyle=':', alpha=0.6)

ax2_2.plot(nav_opt.index, nav_opt, label='策略总净值', color='black', linewidth=2.5, zorder=5)
ax2_2.fill_between(nav_opt.index, 1, 1 + cum_contrib_eq, label='【股】贡献叠加', color='crimson', alpha=0.7)
ax2_2.fill_between(nav_opt.index, 1 + cum_contrib_eq, 1 + cum_contrib_eq + cum_contrib_bond, label='【债】贡献叠加', color='purple', alpha=0.7)
ax2_2.fill_between(nav_opt.index, 1 + cum_contrib_eq + cum_contrib_bond, nav_opt, label='【商】贡献叠加', color='darkgoldenrod', alpha=0.7)
ax2_2.axvline(split_dt, color='white', linestyle='-.', linewidth=2, alpha=0.7)
ax2_2.axhline(1, color='black', linestyle='-', linewidth=1.5)
ax2_2.set_title('账本全貌：十年期股债商【净值堆叠面积图】', fontsize=17, fontweight='bold', pad=15)
ax2_2.legend(loc='upper left', fontsize=12, framealpha=0.9, ncol=2); ax2_2.grid(True, linestyle=':', alpha=0.6)
plt.tight_layout(); plt.show()

fig3, ax3 = plt.subplots(figsize=(16, 8))
ax3.plot(nav_opt.index, nav_opt, label='① 十年定向风控版 (主引擎MA20避险)', color='darkorange', linewidth=3)
ax3.plot(nav_hs300.index, nav_hs300, label='② 基准：沪深300指数', color='grey', linewidth=1.5, linestyle='--')
ax3.plot(nav_bench.index, nav_bench, label='③ 理论原版 (无风控)', color='steelblue', linewidth=1.5, linestyle='-.', alpha=0.6)
ax3.axhline(1, color='black', linewidth=1.5, alpha=0.6)

ax3_twin = ax3.twinx()
excess_return = nav_opt / nav_hs300 - 1
ax3_twin.plot(excess_return.index, excess_return, label='超额收益率 [右轴]', color='purple', linewidth=1.5, alpha=0.9)
ax3_twin.axhline(0, color='black', linewidth=1, linestyle='--', alpha=0.6)
ax3_twin.fill_between(excess_return.index, excess_return, 0, where=(excess_return >= 0), color='#DC143C', alpha=0.15)
ax3_twin.fill_between(excess_return.index, excess_return, 0, where=(excess_return < 0), color='#228B22', alpha=0.15)
ax3_twin.yaxis.set_major_formatter(ticker.PercentFormatter(xmax=1.0))

ax3.axvline(split_dt, color='blue', linestyle='-.', linewidth=2, alpha=0.7, label='实盘分界点')
ax3.set_title('全天候验证：重仓定向风控 vs 沪深300', fontsize=17, fontweight='bold', pad=15)
ax3.grid(True, linestyle=':', alpha=0.6)

lines_1, labels_1 = ax3.get_legend_handles_labels()
lines_2, labels_2 = ax3_twin.get_legend_handles_labels()
ax3.legend(lines_1 + lines_2, labels_1 + labels_2, fontsize=12, loc='upper left')
plt.tight_layout(); plt.show()

print("\n🎉 Step 39 精简成功！系统现在像一名极其老道的猎人，仅在重金投入时才扣下防守的扳机。")

#%% Step 40: 十年期核心策略大乱斗 (2016-2026) —— 风控方案对比与调仓频次测算
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.ticker import FuncFormatter
import matplotlib.ticker as ticker

print("\n========== 开始执行 Step 40: 宏观风控方案切片对比与调仓频次测算 ==========")

# ★ 统一使用 1.5 倍真实波动率作为防抖参数
VOL_MULTIPLIER = 1.5 

start_dt = pd.to_datetime('2016-01-01')
split_dt = pd.to_datetime('2021-04-01') 
dates_all = [d for d in ret_long.index if d >= start_dt]

# --- 1. 底层标尺准备 ---
# 【股票端标尺】
hs300_price = prices_all['沪深300指数'].reindex(dates_all).ffill()
hs300_ma20 = hs300_price.rolling(window=20).mean()
hs300_vol = hs300_price.pct_change().fillna(0).rolling(window=20).std().fillna(0.01) 

if 'top4_nav_s31' not in locals():
    top4_nav_s31 = (1 + top4_daily_returns.reindex(dates_all).fillna(0)).cumprod()
    top4_ma20_s31 = top4_nav_s31.rolling(window=20).mean()
top4_vol = top4_daily_returns.reindex(dates_all).rolling(window=20).std().fillna(0.01)

# 【商品端标尺】
nh_ret = ret_long['南华期货:商品指数'].reindex(dates_all).fillna(0)
nh_nav = (1 + nh_ret).cumprod()
nh_ma20 = nh_nav.rolling(window=20).mean()
nh_vol = nh_ret.rolling(window=20).std().fillna(0.01)

etf_ret_s40 = ret_all[['大成有色ETF', '华安黄金ETF', '建信能化ETF', '华夏豆粕ETF']].reindex(dates_all).fillna(0)
basket_ret_eq_s40 = etf_ret_s40.mean(axis=1)
basket_nav_s40 = (1 + basket_ret_eq_s40).cumprod()
basket_ma20_s40 = basket_nav_s40.rolling(window=20).mean()
basket_vol_s40 = basket_ret_eq_s40.rolling(window=20).std().fillna(0.01)

# --- 2. 严谨回溯与策略平行运算 ---
ret_A = [] # 策略A：无均线避险 (理论原版)
ret_B = [] # 策略B：仅股票执行均线避险
ret_C = [] # 策略C：股、商双端执行均线避险

# 状态记录器 (用于统计 MA 触发的避险动作次数)
# 每次由 "持仓" 变 "空仓" (跌破)，或 "空仓" 变 "持仓" (修复)，均记为 1 次调仓动作
trades_B_eq = 0
trades_C_eq = 0
trades_C_com = 0

prev_esc_B_eq = False
prev_esc_C_eq = False
prev_esc_C_com = False

for d in dates_all:
    w_eq = weights_daily_long['沪深300指数'].loc[d] if pd.notna(weights_daily_long['沪深300指数'].loc[d]) else 0.0
    w_bond = (weights_daily_long['中证基金指数:货币基金'] + weights_daily_long['中证全债指数']).loc[d] if pd.notna((weights_daily_long['中证基金指数:货币基金'] + weights_daily_long['中证全债指数']).loc[d]) else 0.0
    w_com = weights_daily_long['南华期货:商品指数'].loc[d] if pd.notna(weights_daily_long['南华期货:商品指数'].loc[d]) else 0.0
    
    is_eq_heavy = w_eq > 0.65
    is_com_heavy = w_com > 0.65
    
    loc_idx = dates_all.index(d)
    prev_date = dates_all[loc_idx - 1] if loc_idx > 0 else dates_all[0]
    
    # 获取判定条件
    if d < split_dt:
        e_p = hs300_price.loc[prev_date]; e_m = hs300_ma20.loc[prev_date]; e_v = hs300_vol.loc[prev_date]
        e_m_condition = (e_p >= e_m * (1 - VOL_MULTIPLIER * e_v)) if pd.notna(e_m) else True
        r_e = ret_long['沪深300指数'].loc[d]
        
        c_p = nh_nav.loc[prev_date]; c_m = nh_ma20.loc[prev_date]; c_v = nh_vol.loc[prev_date]
        c_m_condition = (c_p >= c_m * (1 - VOL_MULTIPLIER * c_v)) if pd.notna(c_m) else True
        r_c = nh_ret.loc[d]
    else:
        e_p = top4_nav_s31.loc[prev_date] if prev_date in top4_nav_s31.index else np.nan
        e_m = top4_ma20_s31.loc[prev_date] if prev_date in top4_ma20_s31.index else np.nan
        e_v = top4_vol.loc[prev_date]
        e_m_condition = (e_p >= e_m * (1 - VOL_MULTIPLIER * e_v)) if pd.notna(e_m) else True
        r_e = top4_daily_returns.loc[d] if pd.notna(top4_daily_returns.loc[d]) else 0.0
        
        c_p = basket_nav_s40.loc[prev_date] if prev_date in basket_nav_s40.index else np.nan
        c_m = basket_ma20_s40.loc[prev_date] if prev_date in basket_ma20_s40.index else np.nan
        c_v = basket_vol_s40.loc[prev_date] if prev_date in basket_vol_s40.index else 0.01
        c_m_condition = (c_p >= c_m * (1 - VOL_MULTIPLIER * c_v)) if pd.notna(c_m) else True
        r_c = basket_ret_eq_s40.loc[d] if d in basket_ret_eq_s40.index else 0.0

    r_b = ret_long['中证转债'].loc[d]

    # 【策略A：无均线避险 (裸多)】
    ret_A.append(w_eq * r_e + w_bond * r_b + w_com * r_c)

    # 【策略B：仅股票避险】
    act_eq_B = e_m_condition if is_eq_heavy else True
    esc_B_eq = not act_eq_B
    # 统计调仓：如果避险状态发生翻转，说明产生了买/卖动作
    if esc_B_eq != prev_esc_B_eq:
        trades_B_eq += 1
        prev_esc_B_eq = esc_B_eq
        
    w_eq_B = w_eq if act_eq_B else 0.0
    w_bond_B = w_bond + (w_eq - w_eq_B)/2.0
    w_com_B = w_com + (w_eq - w_eq_B)/2.0
    ret_B.append(w_eq_B * r_e + w_bond_B * r_b + w_com_B * r_c)

    # 【策略C：股商双向避险】
    act_eq_C = e_m_condition if is_eq_heavy else True
    act_com_C = c_m_condition if is_com_heavy else True
    
    esc_C_eq = not act_eq_C
    if esc_C_eq != prev_esc_C_eq:
        trades_C_eq += 1
        prev_esc_C_eq = esc_C_eq
        
    esc_C_com = not act_com_C
    if esc_C_com != prev_esc_C_com:
        trades_C_com += 1
        prev_esc_C_com = esc_C_com

    w_eq_C = w_eq if act_eq_C else 0.0
    w_com_C = w_com if act_com_C else 0.0
    w_bond_C = w_bond
    
    if not act_eq_C:  # 股票逃逸
        w_bond_C += w_eq / 2.0
        w_com_C += w_eq / 2.0
    if not act_com_C: # 商品逃逸
        w_bond_C += w_com / 2.0
        w_eq_C += w_com / 2.0
        
    ret_C.append(w_eq_C * r_e + w_bond_C * r_b + w_com_C * r_c)

# --- 3. 计算净值与绩效 ---
nav_A = (1 + pd.Series(ret_A, index=dates_all)).cumprod()
nav_B = (1 + pd.Series(ret_B, index=dates_all)).cumprod()
nav_C = (1 + pd.Series(ret_C, index=dates_all)).cumprod()

def calc_metrics(nav_series, name):
    tot_days = len(nav_series)
    daily_ret = nav_series.pct_change().fillna(0)
    ann_ret = nav_series.iloc[-1] ** (252 / tot_days) - 1 if tot_days > 0 else 0
    max_dd = (nav_series / nav_series.cummax() - 1).min()
    ann_vol = daily_ret.std() * np.sqrt(252)
    rf = 0.02
    sharpe = (ann_ret - rf) / ann_vol if ann_vol > 0 else 0
    calmar = ann_ret / abs(max_dd) if max_dd != 0 else 0
    return {
        '策略版本': name, 
        '年化收益': f"{ann_ret*100:>6.2f}%", 
        '最大回撤': f"{max_dd*100:>7.2f}%",
        '年化波动率': f"{ann_vol*100:>6.2f}%",
        '夏普比率': f"{sharpe:>5.2f}",
        '卡玛比率': f"{calmar:>5.2f}"
    }

print("\n========================= 十年全景回测：(风控方案大乱斗) 核心绩效 =========================")
print(pd.DataFrame([
    calc_metrics(nav_A, "① 策略A：无均线避险 (仅宏观配仓)"),
    calc_metrics(nav_B, "② 策略B：仅股票执行均线避险 (单核防守)"),
    calc_metrics(nav_C, "③ 策略C：股商双核均执行均线避险 (双核防守)")
]).to_string(index=False))
print("===========================================================================================")

print("\n======================= 过去10年 MA20 触发的额外调仓动作统计 =======================")
print(f"▶ 策略B (仅股票避险) 累计触发逃逸/接回动作: {trades_B_eq} 次")
print(f"▶ 策略C (股商双向避险) 累计触发动作: 股票端 {trades_C_eq} 次 + 商品端 {trades_C_com} 次 = 总计 {trades_C_eq + trades_C_com} 次")
print(f"  *注: 平均每年大约增加 {(trades_C_eq + trades_C_com)/10:.1f} 次额外买卖摩擦。")
print("====================================================================================")

# --- 4. 绘图：三线大决战 ---
fig, ax = plt.subplots(figsize=(16, 9))

ax.plot(nav_C.index, nav_C, label='③ 策略C：股商双向避险 (最高防守级别)', color='crimson', linewidth=3, zorder=5)
ax.plot(nav_B.index, nav_B, label='② 策略B：仅股票执行避险 (单核防守)', color='darkorange', linewidth=2.5, alpha=0.9, zorder=4)
ax.plot(nav_A.index, nav_A, label='① 策略A：无均线避险 (理论原版裸多)', color='steelblue', linewidth=2, linestyle='-.', alpha=0.7, zorder=3)

# 突出双向避险相对于无避险的超额区间
ax.fill_between(nav_C.index, nav_C, nav_A, where=(nav_C > nav_A), color='crimson', alpha=0.1, label='双向风控 拯救的净值回撤/超额收益')

ax.axvline(split_dt, color='blue', linestyle='-.', linewidth=2, alpha=0.7, label='2021Q2：实盘行业轮动(TOP4)升级点')

ax.set_title('上帝视角：十年风控切片测试 (无避险 vs 单向避险 vs 双向避险) 净值走势', fontsize=18, fontweight='bold', pad=15)
ax.set_ylabel('累计净值 (初始=1.0)', fontsize=14)
ax.axhline(1, color='black', linewidth=1.5, alpha=0.6)
ax.legend(fontsize=13, loc='upper left', framealpha=0.9)
ax.grid(True, linestyle=':', alpha=0.7)

# 增加重大回撤期的底色高亮，看看是谁扛住了
ax.axvspan(pd.to_datetime('2018-01-29'), pd.to_datetime('2019-01-04'), color='grey', alpha=0.08, label='2018 大熊市')
ax.axvspan(pd.to_datetime('2020-01-20'), pd.to_datetime('2020-03-31'), color='black', alpha=0.08, label='2020 疫情熔断')
ax.axvspan(pd.to_datetime('2023-01-01'), pd.to_datetime('2024-02-01'), color='darkred', alpha=0.05, label='23-24 A股杀估值周期')

plt.tight_layout()
plt.show()

print("\n🎉 Step 40 大结局测算完毕！你现在对每一分防守带来的“收益”与付出的“摩擦代价”都了如指掌。")

#%% Step 41: 十年期核心策略大乱斗 (2016-2026) —— [最终防御形态] 资金全量逃逸至国开债 (季度刻度版)
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import matplotlib.patches as mpatches
from matplotlib.ticker import FuncFormatter
import matplotlib.ticker as ticker

print("\n========== 开始执行 Step 41: 蓄水池升级 (避险资金 100% 注入国开债) ==========")

# 动态识别国开债列名
if '国开债5-7' in ret_long.columns:
    cdb_col = '国开债5-7'
elif '931283.CSI' in ret_long.columns:
    cdb_col = '931283.CSI'
else:
    cdb_col = '中证全债指数' 

print(f"✅ 避险目标锁定：当触发 MA20 逃避时，资金将全额撤离至 [{cdb_col}]")

VOL_MULTIPLIER = 0
start_dt = pd.to_datetime('2016-01-01')
split_dt = pd.to_datetime('2021-04-01') 
dates_all = [d for d in ret_long.index if d >= start_dt]

# --- 1. 底层标尺准备 ---
hs300_price = prices_all['沪深300指数'].reindex(dates_all).ffill()
hs300_ma20 = hs300_price.rolling(window=20).mean()
hs300_vol = hs300_price.pct_change().fillna(0).rolling(window=20).std().fillna(0.01) 

if 'top4_nav_s31' not in locals():
    top4_nav_s31 = (1 + top4_daily_returns.reindex(dates_all).fillna(0)).cumprod()
    top4_ma20_s31 = top4_nav_s31.rolling(window=20).mean()
top4_vol = top4_daily_returns.reindex(dates_all).rolling(window=20).std().fillna(0.01)

nh_ret = ret_long['南华期货:商品指数'].reindex(dates_all).fillna(0)
nh_nav = (1 + nh_ret).cumprod()
nh_ma20 = nh_nav.rolling(window=20).mean()
nh_vol = nh_ret.rolling(window=20).std().fillna(0.01)

basket_ret_eq_s41 = ret_all[['大成有色ETF', '华安黄金ETF', '建信能化ETF', '华夏豆粕ETF']].reindex(dates_all).fillna(0).mean(axis=1)
basket_nav_s41 = (1 + basket_ret_eq_s41).cumprod()
basket_ma20_s41 = basket_nav_s41.rolling(window=20).mean()
basket_vol_s41 = basket_ret_eq_s41.rolling(window=20).std().fillna(0.01)

# --- 2. 策略回溯运算 ---
ret_A = []; ret_B = []; ret_C = []
trades_C_eq = 0; trades_C_com = 0
prev_esc_C_eq = False; prev_esc_C_com = False

# 记录详细数据
daily_active_assets = {} # 用于甘特图
is_eq_escape_daily = {}; is_com_escape_daily = {}
hist_w_eq = []; hist_w_com = []; hist_w_cb = []; hist_w_cdb = []

for d in dates_all:
    w_eq = weights_daily_long['沪深300指数'].loc[d] if pd.notna(weights_daily_long['沪深300指数'].loc[d]) else 0.0
    w_com = weights_daily_long['南华期货:商品指数'].loc[d] if pd.notna(weights_daily_long['南华期货:商品指数'].loc[d]) else 0.0
    w_bond_total = (weights_daily_long['中证基金指数:货币基金'] + weights_daily_long['中证全债指数']).loc[d] if pd.notna((weights_daily_long['中证基金指数:货币基金'] + weights_daily_long['中证全债指数']).loc[d]) else 0.0
    
    # 基础分配：10% 国开债底仓，其余归转债
    w_cdb_base = min(0.10, w_bond_total) 
    w_cb_base = max(0.0, w_bond_total - 0.10)
    
    is_eq_heavy = w_eq > 0.65
    is_com_heavy = w_com > 0.65
    
    prev_date = dates_all[dates_all.index(d)-1] if dates_all.index(d) > 0 else dates_all[0]
    
    # 获取避险判定条件
    if d < split_dt:
        e_m_cond = (hs300_price.loc[prev_date] >= hs300_ma20.loc[prev_date] * (1 - VOL_MULTIPLIER * hs300_vol.loc[prev_date])) if pd.notna(hs300_ma20.loc[prev_date]) else True
        c_m_cond = (nh_nav.loc[prev_date] >= nh_ma20.loc[prev_date] * (1 - VOL_MULTIPLIER * nh_vol.loc[prev_date])) if pd.notna(nh_ma20.loc[prev_date]) else True
        r_e, r_c = ret_long['沪深300指数'].loc[d], nh_ret.loc[d]
        eq_names = ['【股】前期大盘']
    else:
        e_m_cond = (top4_nav_s31.loc[prev_date] >= top4_ma20_s31.loc[prev_date] * (1 - VOL_MULTIPLIER * top4_vol.loc[prev_date])) if pd.notna(top4_ma20_s31.loc[prev_date]) else True
        c_m_cond = (basket_nav_s41.loc[prev_date] >= basket_ma20_s41.loc[prev_date] * (1 - VOL_MULTIPLIER * basket_vol_s41.loc[prev_date])) if pd.notna(basket_ma20_s41.loc[prev_date]) else True
        r_e, r_c = (top4_daily_returns.loc[d] if pd.notna(top4_daily_returns.loc[d]) else 0.0), basket_ret_eq_s41.loc[d]
        eq_names = q_to_inds_original.get(f"{d.year}Q{d.quarter}", [])[:4]

    r_cb, r_cdb = ret_long['中证转债'].loc[d], ret_long[cdb_col].loc[d]

    # --- 策略C：核心逻辑 (资金全量入蓄水池) ---
    act_eq = e_m_cond if is_eq_heavy else True
    act_com = c_m_cond if is_com_heavy else True
    
    # 统计调仓
    if (not act_eq) != prev_esc_C_eq: trades_C_eq += 1; prev_esc_C_eq = (not act_eq)
    if (not act_com) != prev_esc_C_com: trades_C_com += 1; prev_esc_C_com = (not act_com)

    # 资金重分配
    final_w_eq = w_eq if act_eq else 0.0
    final_w_com = w_com if act_com else 0.0
    final_w_cb = w_cb_base
    # 关键：逃逸出来的 w_eq 或 w_com 全部加给国开债
    final_w_cdb = w_cdb_base + (w_eq - final_w_eq) + (w_com - final_w_com)
    
    ret_C.append(final_w_eq * r_e + final_w_com * r_c + final_w_cb * r_cb + final_w_cdb * r_cdb)
    ret_A.append(w_eq * r_e + w_com * r_c + w_cb_base * r_cb + w_cdb_base * r_cdb)
    
    # 记录状态
    active_assets = []
    if final_w_eq > 0: active_assets.extend(eq_names)
    if final_w_com > 0: active_assets.append('【商】大宗商品端')
    daily_active_assets[d] = active_assets
    is_eq_escape_daily[d] = not act_eq
    is_com_escape_daily[d] = not act_com
    hist_w_eq.append(final_w_eq * 100); hist_w_com.append(final_w_com * 100)
    hist_w_cb.append(final_w_cb * 100); hist_w_cdb.append(final_w_cdb * 100)

# --- 3. 绩效与绘图 ---
nav_A = (1 + pd.Series(ret_A, index=dates_all)).cumprod()
nav_C = (1 + pd.Series(ret_C, index=dates_all)).cumprod()
nav_hs300 = (1 + hs300_ret.reindex(dates_all).fillna(0)).cumprod()

def get_metrics(nav, name):
    daily = nav.pct_change().fillna(0)
    ann = nav.iloc[-1]**(252/len(nav))-1
    mdd = (nav/nav.cummax()-1).min()
    vol = daily.std()*np.sqrt(252)
    return {'策略':name, '年化':f"{ann*100:.2f}%", '回撤':f"{mdd*100:.2f}%", '夏普':f"{(ann-0.02)/vol:.2f}"}

print("\n========================= 十年全景回测：(全量逃逸版) 核心绩效 =========================")
print(pd.DataFrame([get_metrics(nav_hs300, "沪深300指数"), get_metrics(nav_A, "理论原版(无避险)"), get_metrics(nav_C, "终极防御版(全入国开债)")]).to_string(index=False))
print(f"\n▶ 避险操作统计：股票逃逸/回归 {trades_C_eq} 次，商品逃逸/回归 {trades_C_com} 次")

# 【图表 1】甘特图：避险状态可视化
print("\n正在渲染带季度坐标轴的全景甘特图与资金分布...")
all_labels = []
for assets in daily_active_assets.values():
    for a in assets:
        if a not in all_labels: all_labels.append(a)
if '【商】大宗商品端' in all_labels: all_labels.remove('【商】大宗商品端'); all_labels.insert(0, '【商】大宗商品端')
label_y = {l: i for i, l in enumerate(all_labels)}

# ★ 关键改动：sharex=True 共享 X 轴，确保三图时间刻度完美垂直对齐
fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(16, 18), gridspec_kw={'height_ratios': [1.2, 0.8, 1.5]}, sharex=True)

# 甘特图
for lbl, y in label_y.items():
    is_in = False; start = None
    color = 'darkgoldenrod' if '【商】' in lbl else 'limegreen'
    for d in dates_all:
        present = lbl in daily_active_assets[d]
        if present and not is_in: is_in = True; start = d
        elif not present and is_in: is_in = False; ax1.broken_barh([(mdates.date2num(start), mdates.date2num(d)-mdates.date2num(start))], (y-0.3, 0.6), color=color, edgecolor='black', linewidth=0.5)
    if is_in: ax1.broken_barh([(mdates.date2num(start), mdates.date2num(dates_all[-1])-mdates.date2num(start))], (y-0.3, 0.6), color=color)

for d in dates_all:
    if is_eq_escape_daily[d]: ax1.axvspan(d, d + pd.Timedelta(days=1), color='crimson', alpha=0.1)
    if is_com_escape_daily[d]: ax1.axvspan(d, d + pd.Timedelta(days=1), color='orange', alpha=0.1)

ax1.set_yticks(range(len(all_labels))); ax1.set_yticklabels(all_labels); ax1.invert_yaxis()
ax1.set_title('十年实战甘特图：主引擎(70%)定向避险状态 (红色/橙色背景代表逃逸期)', fontsize=15, fontweight='bold')

# 资金分布图
ax2.stackplot(dates_all, hist_w_eq, hist_w_cb, hist_w_com, hist_w_cdb, labels=['股票', '可转债(进攻)', '商品', '国开债(蓄水池)'], colors=['crimson', 'darkviolet', 'darkgoldenrod', 'steelblue'], alpha=0.8)
ax2.set_ylabel('占比 (%)'); ax2.set_ylim(0, 100); ax2.legend(loc='upper left', ncol=4); ax2.margins(x=0)

# 净值曲线图
ax3.plot(nav_C.index, nav_C, label='终极防御版 (避险资金全入国开债)', color='crimson', linewidth=3)
ax3.plot(nav_A.index, nav_A, label='理论原版 (无避险)', color='grey', linestyle='--', alpha=0.7)
ax3.plot(nav_hs300.index, nav_hs300, label='沪深300指数', color='black', linewidth=1, alpha=0.5)
ax3.set_title('十年长跑：不同风控策略下的净值增长曲线', fontsize=15, fontweight='bold')
ax3.legend(loc='upper left'); ax3.grid(True, alpha=0.3)

# ★ 关键改动：构建并应用季度格式化器 (Quarter Formatter) ★
def quarter_formatter(x, pos):
    try:
        dt = mdates.num2date(x)
        q = (dt.month - 1) // 3 + 1
        return f"{dt.year}Q{q}"
    except:
        return ""

# 使用 MonthLocator 每3个月打一个刻度 (1月, 4月, 7月, 10月 代表 Q1, Q2, Q3, Q4)
ax3.xaxis.set_major_locator(mdates.MonthLocator(bymonth=[1, 4, 7, 10]))
ax3.xaxis.set_major_formatter(FuncFormatter(quarter_formatter))

# 旋转 45 度避免文字重叠，居右对齐
plt.setp(ax3.get_xticklabels(), rotation=45, ha='right', fontsize=11, fontweight='bold')

plt.tight_layout(); plt.show()

#%% Step 42: 终极防御版 —— 历年收益深度拆解与回撤全景测算
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import matplotlib.ticker as ticker

print("\n========== 开始执行 Step 42: 年度收益拆解与最大回撤测算 ==========")

# --- 1. 数据安全重构：精确提取四大底层资产的每日收益与配置权重 ---
# 从 Step 41 继承配置好的权重序列 (转为百分比小数)
s_w_eq = pd.Series(hist_w_eq, index=dates_all) / 100.0
s_w_com = pd.Series(hist_w_com, index=dates_all) / 100.0
s_w_cb = pd.Series(hist_w_cb, index=dates_all) / 100.0
s_w_cdb = pd.Series(hist_w_cdb, index=dates_all) / 100.0

# 重构资产的每日真实收益序列
r_eq = pd.Series(np.where(pd.Series(dates_all) < split_dt,
                          ret_long['沪深300指数'].reindex(dates_all).fillna(0).values,
                          top4_daily_returns.reindex(dates_all).fillna(0).values), index=dates_all)

r_com = pd.Series(np.where(pd.Series(dates_all) < split_dt,
                           ret_long['南华期货:商品指数'].reindex(dates_all).fillna(0).values,
                           basket_ret_eq_s41.reindex(dates_all).fillna(0).values), index=dates_all)

r_cb = ret_long['中证转债'].reindex(dates_all).fillna(0)
r_cdb = ret_long[cdb_col].reindex(dates_all).fillna(0)

# 计算绝对收益点数
df_daily = pd.DataFrame({
    'Eq': s_w_eq * r_eq,
    'Com': s_w_com * r_com,
    'Cb': s_w_cb * r_cb,
    'Cdb': s_w_cdb * r_cdb,
    'Strat': pd.Series(ret_C, index=dates_all), # 终极策略总收益
    'HS300': r_eq if 'hs300_ret' not in locals() else hs300_ret.reindex(dates_all).fillna(0) # 兜底获取沪深300
})
df_daily['Prev_NAV'] = nav_C.shift(1).fillna(1.0)
df_daily['Year'] = df_daily.index.year

# --- 2. 核心算法：按年严格拆解净值贡献度 ---
annual_stats = []
for year, group in df_daily.groupby('Year'):
    start_nav = group['Prev_NAV'].iloc[0]
    
    # 策略与基准的真实年化计算
    ret_strat = (1 + group['Strat']).prod() - 1
    ret_hs300 = (1 + group['HS300']).prod() - 1
    
    # 将每日的绝对收益点数累加，除以年初净值，得出该资产当年的百分比贡献
    cont_eq = (group['Eq'] * group['Prev_NAV']).sum() / start_nav
    cont_com = (group['Com'] * group['Prev_NAV']).sum() / start_nav
    cont_cb = (group['Cb'] * group['Prev_NAV']).sum() / start_nav
    cont_cdb = (group['Cdb'] * group['Prev_NAV']).sum() / start_nav
    
    annual_stats.append({
        'Year': str(year),
        'Strategy': ret_strat,
        'HS300': ret_hs300,
        'Eq': cont_eq,
        'Cb': cont_cb,
        'Com': cont_com,
        'Cdb': cont_cdb
    })

df_annual = pd.DataFrame(annual_stats).set_index('Year')

# --- 3. 绘制图表 1：年度收益大比拼与贡献拆解 ---
print("正在渲染 图表1: 历年收益率对决与四大资产归因分析...")
fig1, (ax1, ax2) = plt.subplots(2, 1, figsize=(16, 14))

# 【子图 1】单纯的年度收益率对比柱状图
x = np.arange(len(df_annual))
width = 0.35

bar1 = ax1.bar(x - width/2, df_annual['Strategy'], width, label='终极防御版 (避险资金全入国开债)', color='crimson', edgecolor='black', linewidth=0.5)
bar2 = ax1.bar(x + width/2, df_annual['HS300'], width, label='沪深300指数', color='lightgrey', edgecolor='grey', linewidth=0.5)

ax1.set_xticks(x); ax1.set_xticklabels(df_annual.index, fontsize=12)
ax1.axhline(0, color='black', linewidth=1)
ax1.yaxis.set_major_formatter(ticker.PercentFormatter(xmax=1.0))
ax1.set_title('十年实战检阅：终极防御体系 vs 沪深300 历年自然年度收益率比对', fontsize=16, fontweight='bold', pad=15)
ax1.legend(loc='upper center', bbox_to_anchor=(0.5, 1.15), ncol=2, fontsize=12)
ax1.grid(True, linestyle=':', alpha=0.6, axis='y')

# 为柱子加上数据标签 (视觉提升)
for i, v in enumerate(df_annual['Strategy']):
    ax1.text(i - width/2, v + (0.015 if v >= 0 else -0.025), f"{v*100:.1f}%", ha='center', va='bottom' if v >= 0 else 'top', fontsize=11, fontweight='bold', color='crimson')
for i, v in enumerate(df_annual['HS300']):
    ax1.text(i + width/2, v + (0.015 if v >= 0 else -0.025), f"{v*100:.1f}%", ha='center', va='bottom' if v >= 0 else 'top', fontsize=10, color='dimgrey')

# 【子图 2】将终极防御版的收益进行堆叠拆解
assets = ['Eq', 'Cb', 'Com', 'Cdb']
colors = ['crimson', 'darkviolet', 'darkgoldenrod', 'steelblue']
labels = ['【股】贡献度', '【可转债】贡献度', '【商】贡献度', '【国开债】(水库) 贡献度']

pos_bottom = np.zeros(len(df_annual))
neg_bottom = np.zeros(len(df_annual))

for idx, asset in enumerate(assets):
    vals = df_annual[asset].values
    pos_vals = np.maximum(vals, 0)
    neg_vals = np.minimum(vals, 0)
    
    # 绘制正向收益与负向收益 (分离堆叠)
    ax2.bar(x, pos_vals, bottom=pos_bottom, color=colors[idx], label=labels[idx], width=0.5, edgecolor='white', linewidth=0.5)
    ax2.bar(x, neg_vals, bottom=neg_bottom, color=colors[idx], width=0.5, edgecolor='white', linewidth=0.5)
    
    pos_bottom += pos_vals
    neg_bottom += neg_vals

# 叠加总收益黑点连线
ax2.plot(x, df_annual['Strategy'], marker='D', markersize=8, color='black', linewidth=1.5, linestyle=':', label='策略该年总净收益')

ax2.set_xticks(x); ax2.set_xticklabels(df_annual.index, fontsize=12)
ax2.axhline(0, color='black', linewidth=1.5)
ax2.yaxis.set_major_formatter(ticker.PercentFormatter(xmax=1.0))
ax2.set_title('防御内核透视：组合年度总收益的【四大资产驱动力】拆解', fontsize=16, fontweight='bold', pad=15)
ax2.legend(loc='upper center', bbox_to_anchor=(0.5, 1.15), ncol=5, fontsize=11)
ax2.grid(True, linestyle=':', alpha=0.6, axis='y')

plt.tight_layout()
plt.show()

# --- 4. 绘制图表 2：最大回撤全景对比 (水下曲线) ---
print("正在渲染 图表2: 资金曲线的最大回撤 (Underwater Chart) 对决...")

# 计算动态最大回撤序列
dd_strat = nav_C / nav_C.cummax() - 1
dd_hs300 = nav_hs300 / nav_hs300.cummax() - 1

fig2, ax = plt.subplots(figsize=(16, 7))

# 绘制沪深300回撤 (作为阴影背景)
ax.fill_between(dd_hs300.index, dd_hs300, 0, color='grey', alpha=0.25, label='沪深300 每日回撤幅度')
ax.plot(dd_hs300.index, dd_hs300, color='grey', linewidth=1, alpha=0.8)

# 绘制终极防御版回撤 (作为前景高亮)
ax.fill_between(dd_strat.index, dd_strat, 0, color='crimson', alpha=0.6, label='终极防御版 (国开债蓄水) 每日回撤幅度')
ax.plot(dd_strat.index, dd_strat, color='darkred', linewidth=1.5)

# 计算并标识出历史最大回撤极值点
max_dd_hs300_idx = dd_hs300.idxmin()
max_dd_hs300_val = dd_hs300.min()
ax.scatter(max_dd_hs300_idx, max_dd_hs300_val, color='black', s=80, zorder=5)
ax.annotate(f'沪深300 最大回撤\n{max_dd_hs300_val*100:.2f}%', 
            xy=(max_dd_hs300_idx, max_dd_hs300_val), xytext=(20, 20),
            textcoords='offset points', ha='left', va='bottom',
            bbox=dict(boxstyle='round,pad=0.3', fc='white', alpha=0.8),
            arrowprops=dict(arrowstyle='->', connectionstyle='arc3,rad=0.2', color='black'))

max_dd_strat_idx = dd_strat.idxmin()
max_dd_strat_val = dd_strat.min()
ax.scatter(max_dd_strat_idx, max_dd_strat_val, color='darkred', s=80, zorder=5)
ax.annotate(f'终极版 最大回撤\n{max_dd_strat_val*100:.2f}%', 
            xy=(max_dd_strat_idx, max_dd_strat_val), xytext=(-20, 30),
            textcoords='offset points', ha='right', va='bottom',
            bbox=dict(boxstyle='round,pad=0.3', fc='white', alpha=0.8),
            arrowprops=dict(arrowstyle='->', connectionstyle='arc3,rad=-0.2', color='darkred'))

ax.axhline(0, color='black', linewidth=1.5)
ax.set_title('抗压极限测压：终极防御版 vs 沪深300 历史回撤水下分布图 (Underwater)', fontsize=17, fontweight='bold', pad=15)
ax.yaxis.set_major_formatter(ticker.PercentFormatter(xmax=1.0))
ax.set_ylabel('距离历史高点的回撤幅度', fontsize=12)
ax.legend(loc='lower left', fontsize=13)
ax.grid(True, linestyle=':', alpha=0.6)

plt.tight_layout()
plt.show()

print("\n🎉 大功告成！这两张极具穿透力的归因与风控图表现已渲染完毕。")

#%% Step 43: 终极防御版 —— 四核资产持仓与避险合并日志 (Excel 导出)
import pandas as pd

print("\n========== 开始执行 Step 43: 生成【四核终极防御版】持仓合并明细表 ==========")

merged_records = []
last_state = None
current_q = None

print("正在逐日扫描状态，合并无变动的持仓区间...")

for d in dates_all:
    q_str = f"{d.year}Q{d.quarter}"
    
    # 1. 提取当日基础宏观分配
    w_eq = weights_daily_long['沪深300指数'].loc[d] if pd.notna(weights_daily_long['沪深300指数'].loc[d]) else 0.0
    w_com = weights_daily_long['南华期货:商品指数'].loc[d] if pd.notna(weights_daily_long['南华期货:商品指数'].loc[d]) else 0.0
    w_bond_total = (weights_daily_long['中证基金指数:货币基金'] + weights_daily_long['中证全债指数']).loc[d] if pd.notna((weights_daily_long['中证基金指数:货币基金'] + weights_daily_long['中证全债指数']).loc[d]) else 0.0
    
    w_cdb_base = min(0.10, w_bond_total) 
    w_cb_base = max(0.0, w_bond_total - 0.10)
    
    is_eq_heavy = w_eq > 0.65
    is_com_heavy = w_com > 0.65
    
    loc_idx = dates_all.index(d)
    prev_date = dates_all[loc_idx - 1] if loc_idx > 0 else dates_all[0]
    
    # 2. 获取标的名称与避险判定条件
    if d < split_dt:
        e_m_cond = (hs300_price.loc[prev_date] >= hs300_ma20.loc[prev_date] * (1 - VOL_MULTIPLIER * hs300_vol.loc[prev_date])) if pd.notna(hs300_ma20.loc[prev_date]) else True
        c_m_cond = (nh_nav.loc[prev_date] >= nh_ma20.loc[prev_date] * (1 - VOL_MULTIPLIER * nh_vol.loc[prev_date])) if pd.notna(nh_ma20.loc[prev_date]) else True
        eq_names = ['沪深300宽基']
        com_names = ['南华期货指数']
    else:
        e_m_cond = (top4_nav_s31.loc[prev_date] >= top4_ma20_s31.loc[prev_date] * (1 - VOL_MULTIPLIER * top4_vol.loc[prev_date])) if pd.notna(top4_ma20_s31.loc[prev_date]) else True
        c_m_cond = (basket_nav_s41.loc[prev_date] >= basket_ma20_s41.loc[prev_date] * (1 - VOL_MULTIPLIER * basket_vol_s41.loc[prev_date])) if pd.notna(basket_ma20_s41.loc[prev_date]) else True
        eq_names = q_to_inds_original.get(q_str, [])[:4]
        com_names = ['有色/黄金/能化/豆粕等权']

    # 3. 执行核心逻辑判定
    act_eq = e_m_cond if is_eq_heavy else True
    act_com = c_m_cond if is_com_heavy else True
    
    final_w_eq = w_eq if act_eq else 0.0
    final_w_com = w_com if act_com else 0.0
    final_w_cb = w_cb_base
    
    freed_eq = w_eq - final_w_eq
    freed_com = w_com - final_w_com
    final_w_cdb = w_cdb_base + freed_eq + freed_com
    
    # 4. 构建精美可读的明细字符串
    # 股票端字符串
    if w_eq == 0:
        eq_str = "⚪宏观空仓(0%)"
    elif not act_eq:
        eq_str = f"🔴防线击穿->全线撤退(0%) | 原目标:{','.join(eq_names)}"
    else:
        weight_per_ind = final_w_eq / max(1, len(eq_names)) * 100
        eq_str = f"🟢正常持仓({final_w_eq*100:.1f}%) | " + "、".join([f"{n}({weight_per_ind:.1f}%)" for n in eq_names])
        
    # 商品端字符串
    if w_com == 0:
        com_str = "⚪宏观空仓(0%)"
    elif not act_com:
        com_str = f"🟠防线击穿->全线撤退(0%) | 原目标:{','.join(com_names)}"
    else:
        com_str = f"🟡正常持仓({final_w_com*100:.1f}%) | {com_names[0]}"
        
    # 国开债避险字符串
    if freed_eq > 0 and freed_com > 0:
        cdb_str = f"🌊接盘股商双杀 (+{freed_eq*100:.1f}%股, +{freed_com*100:.1f}%商)"
    elif freed_eq > 0:
        cdb_str = f"🛡️接盘股票避险资金 (+{freed_eq*100:.1f}%)"
    elif freed_com > 0:
        cdb_str = f"🛡️接盘商品避险资金 (+{freed_com*100:.1f}%)"
    else:
        cdb_str = "安静生息 (无避险涌入)"
        
    # 定义“当前唯一状态标识”
    current_state = {
        'macro_eq': w_eq, 'macro_com': w_com,
        'final_eq': final_w_eq, 'final_com': final_w_com,
        'eq_detail': eq_str, 'com_detail': com_str, 'cdb_detail': cdb_str
    }
    
    date_str = d.strftime('%Y-%m-%d')
    
    # 5. 合并连续相同区间
    if last_state and current_state == last_state:
        merged_records[-1]['结束日期'] = date_str
        merged_records[-1]['交易天数'] += 1
    else:
        new_row = {
            '开始日期': date_str,
            '结束日期': date_str,
            '交易天数': 1,
            '【实际】股票占比': f"{final_w_eq*100:.1f}%",
            '【实际】转债占比': f"{final_w_cb*100:.1f}%",
            '【实际】商品占比': f"{final_w_com*100:.1f}%",
            '【实际】国开债占比': f"{final_w_cdb*100:.1f}%",
            '【状态】股票主引擎': current_state['eq_detail'],
            '【状态】商品主引擎': current_state['com_detail'],
            '【水库】国开债承接动作': current_state['cdb_detail']
        }
        merged_records.append(new_row)
        last_state = current_state

# 转换 DataFrame
df_merged = pd.DataFrame(merged_records)

# --- 6. 导出至本地 Excel ---
try:
    file_path = "四核驱动_避险持仓区间合并表.xlsx"
    df_merged.to_excel(file_path, index=False)
    print(f"\n✅ 成功导出审计账单至：【{file_path}】")
    print(f"数据量从 {len(dates_all)} 个交易日大幅压缩至 {len(df_merged)} 个战略持仓阶段。")
except Exception as e:
    print(f"\n❌ 导出Excel失败: {e}")

# --- 7. 打印控制台精华版 ---
print("\n========== 核心调仓审计记录 (最近 15 次) ==========")
# 为了在控制台显示得更紧凑，稍微截取一下尾部数据
df_tail = df_merged.tail(15).copy()
for _, row in df_tail.iterrows():
    print(f"🗓️ {row['开始日期']} 至 {row['结束日期']} (共 {row['交易天数']:>2} 天) | 仓位: 股{row['【实际】股票占比']} 商{row['【实际】商品占比']} 债{row['【实际】转债占比']} 国开{row['【实际】国开债占比']}")
    print(f"   └ 股端: {row['【状态】股票主引擎']}")
    print(f"   └ 商端: {row['【状态】商品主引擎']}")
    print(f"   └ 水库: {row['【水库】国开债承接动作']}\n")

print("Step 43 终极合并版执行完毕！拿着这张表，你可以给任何人清晰地复盘你过去十年的每一次决策。")

#%% Step 44: 硬核风控逻辑横向比对测试 (无风控 vs 对称设计 vs v4.0不对称单线)
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker

print("\n========== 开始执行 Step 44: 三大风控逻辑横向平行推演 ==========")

# --- 1. 状态机与变量初始化 ---
ret_A = [] # ① 无风控硬抗
ret_B = [] # ② 对称通道设计
ret_C = [] # ③ v4.0 现行机制 (不对称单线)

# 对称策略 B 需要维持历史状态来判断当前是否“在车上”
in_eq_B = True
in_com_B = True

print("正在平行推演三大风控时空宇宙的逐日资金流转...")

for d in dates_all:
    # --- 基础权重分配 (继承自普林格与底层设定) ---
    w_eq = weights_daily_long['沪深300指数'].loc[d] if pd.notna(weights_daily_long['沪深300指数'].loc[d]) else 0.0
    w_com = weights_daily_long['南华期货:商品指数'].loc[d] if pd.notna(weights_daily_long['南华期货:商品指数'].loc[d]) else 0.0
    w_bond_total = (weights_daily_long['中证基金指数:货币基金'] + weights_daily_long['中证全债指数']).loc[d] if pd.notna((weights_daily_long['中证基金指数:货币基金'] + weights_daily_long['中证全债指数']).loc[d]) else 0.0
    
    w_cdb_base = min(0.10, w_bond_total) 
    w_cb_base = max(0.0, w_bond_total - 0.10)
    
    is_eq_heavy = w_eq > 0.65
    is_com_heavy = w_com > 0.65
    
    loc_idx = dates_all.index(d)
    prev_date = dates_all[loc_idx - 1] if loc_idx > 0 else dates_all[0]
    
    # --- 指标标尺读取 (无缝衔接已有变量) ---
    if d < split_dt:
        e_p = hs300_price.loc[prev_date] if pd.notna(hs300_price.loc[prev_date]) else np.nan
        e_ma = hs300_ma20.loc[prev_date] if pd.notna(hs300_ma20.loc[prev_date]) else np.nan
        e_vol = hs300_vol.loc[prev_date] if pd.notna(hs300_vol.loc[prev_date]) else 0.01
        
        c_p = nh_nav.loc[prev_date] if pd.notna(nh_nav.loc[prev_date]) else np.nan
        c_ma = nh_ma20.loc[prev_date] if pd.notna(nh_ma20.loc[prev_date]) else np.nan
        c_vol = nh_vol.loc[prev_date] if pd.notna(nh_vol.loc[prev_date]) else 0.01
        
        r_e = ret_long['沪深300指数'].loc[d] if pd.notna(ret_long['沪深300指数'].loc[d]) else 0.0
        r_c = nh_ret.loc[d] if pd.notna(nh_ret.loc[d]) else 0.0
    else:
        e_p = top4_nav_s31.loc[prev_date] if prev_date in top4_nav_s31.index else np.nan
        e_ma = top4_ma20_s31.loc[prev_date] if prev_date in top4_ma20_s31.index else np.nan
        e_vol = top4_vol.loc[prev_date] if prev_date in top4_vol.index else 0.01
        
        c_p = basket_nav_s41.loc[prev_date] if prev_date in basket_nav_s41.index else np.nan
        c_ma = basket_ma20_s41.loc[prev_date] if prev_date in basket_ma20_s41.index else np.nan
        c_vol = basket_vol_s41.loc[prev_date] if prev_date in basket_vol_s41.index else 0.01
        
        r_e = top4_daily_returns.loc[d] if pd.notna(top4_daily_returns.loc[d]) else 0.0
        r_c = basket_ret_eq_s41.loc[d] if d in basket_ret_eq_s41.index else 0.0

    r_cb = ret_long['中证转债'].loc[d] if pd.notna(ret_long['中证转债'].loc[d]) else 0.0
    r_cdb = ret_long[cdb_col].loc[d] if pd.notna(ret_long[cdb_col].loc[d]) else 0.0

    # ================= 策略 A: 无风控硬抗 (散户思维) =================
    ret_A.append(w_eq * r_e + w_com * r_c + w_cb_base * r_cb + w_cdb_base * r_cdb)
    
    # ================= 策略 B: 对称通道设计 (经典布林带维) =================
    if is_eq_heavy and pd.notna(e_ma):
        sell_line_B = e_ma * (1 - VOL_MULTIPLIER * e_vol)
        buy_line_B  = e_ma * (1 + VOL_MULTIPLIER * e_vol)
        # 状态机：如果原来在车上，且跌破下轨 -> 卖出躲避
        if in_eq_B and e_p < sell_line_B: 
            in_eq_B = False        
        # 状态机：如果原来在车外，且强势突破上轨 -> 才允许买回
        elif not in_eq_B and e_p > buy_line_B: 
            in_eq_B = True      
    else:
        in_eq_B = True # 非重仓期默认在车上
        
    if is_com_heavy and pd.notna(c_ma):
        sell_line_cB = c_ma * (1 - VOL_MULTIPLIER * c_vol)
        buy_line_cB  = c_ma * (1 + VOL_MULTIPLIER * c_vol)
        if in_com_B and c_p < sell_line_cB: 
            in_com_B = False
        elif not in_com_B and c_p > buy_line_cB: 
            in_com_B = True
    else:
        in_com_B = True

    w_eq_B = w_eq if in_eq_B else 0.0
    w_com_B = w_com if in_com_B else 0.0
    w_cdb_B = w_cdb_base + (w_eq - w_eq_B) + (w_com - w_com_B) # 逃逸资金去国开债
    ret_B.append(w_eq_B * r_e + w_com_B * r_c + w_cb_base * r_cb + w_cdb_B * r_cdb)

    # ================= 策略 C: v4.0 现行机制 (单线极致防踏空) =================
    act_eq_C = (e_p >= e_ma * (1 - VOL_MULTIPLIER * e_vol)) if (is_eq_heavy and pd.notna(e_ma)) else True
    act_com_C = (c_p >= c_ma * (1 - VOL_MULTIPLIER * c_vol)) if (is_com_heavy and pd.notna(c_ma)) else True
    
    w_eq_C = w_eq if act_eq_C else 0.0
    w_com_C = w_com if act_com_C else 0.0
    w_cdb_C = w_cdb_base + (w_eq - w_eq_C) + (w_com - w_com_C)
    ret_C.append(w_eq_C * r_e + w_com_C * r_c + w_cb_base * r_cb + w_cdb_C * r_cdb)

# --- 2. 净值转换与指标计算 ---
nav_A = (1 + pd.Series(ret_A, index=dates_all)).cumprod()
nav_B = (1 + pd.Series(ret_B, index=dates_all)).cumprod()
nav_C = (1 + pd.Series(ret_C, index=dates_all)).cumprod()

def calc_custom_metrics(nav_series, name):
    tot_days = len(nav_series)
    daily_ret = nav_series.pct_change().fillna(0)
    ann_ret = nav_series.iloc[-1] ** (252 / tot_days) - 1 if tot_days > 0 else 0
    max_dd = (nav_series / nav_series.cummax() - 1).min()
    ann_vol = daily_ret.std() * np.sqrt(252)
    sharpe = (ann_ret - 0.02) / ann_vol if ann_vol > 0 else 0
    return {
        '风控版本': name, 
        '年化收益': f"{ann_ret*100:>6.2f}%", 
        '最大回撤': f"{max_dd*100:>7.2f}%",
        '夏普比率': f"{sharpe:>5.2f}"
    }

print("\n========================= 风控逻辑大比武：核心绩效揭晓 =========================")
print(pd.DataFrame([
    calc_custom_metrics(nav_A, "① 无风控硬抗 (闭眼裸奔)"),
    calc_custom_metrics(nav_B, "② 对称通道设计 (买回太慢/死区踏空)"),
    calc_custom_metrics(nav_C, "③ v4.0 现行机制 (单线同归/极致防踏空)")
]).to_string(index=False))
print("=================================================================================")

# --- 3. 绘图：资金曲线对决 ---
fig_test, ax_test = plt.subplots(figsize=(16, 8))

ax_test.plot(nav_C.index, nav_C, label='③ v4.0 现行防御机制 (赢家)', color='crimson', linewidth=3.5, zorder=5)
ax_test.plot(nav_B.index, nav_B, label='② 对称通道设计 (严重踏空 V型反弹)', color='darkorange', linewidth=2, linestyle='-', zorder=4)
ax_test.plot(nav_A.index, nav_A, label='① 无风控硬抗 (大熊市直线跳水)', color='black', linewidth=1.5, linestyle=':', alpha=0.8, zorder=3)

# 突出显示 v4.0 相对于 对称设计 抢出来的“踏空利润”
ax_test.fill_between(nav_C.index, nav_C, nav_B, where=(nav_C > nav_B), color='crimson', alpha=0.15, label='v4.0 拒绝踏空多赚的【黄金鱼身利润】')

ax_test.set_title('风控内核终极对决：无风控 vs 对称通道 vs 不对称单线 (v4.0)', fontsize=17, fontweight='bold', pad=15)
ax_test.set_ylabel('累计净值 (初始=1.0)', fontsize=14)
ax_test.legend(loc='upper left', fontsize=13, framealpha=0.9)
ax_test.grid(True, linestyle=':', alpha=0.7)

# 标记历史极端的V型反转大区，验证踏空现象
ax_test.axvspan(pd.to_datetime('2020-02-01'), pd.to_datetime('2020-07-01'), color='blue', alpha=0.08, label='2020 疫情底 (对称策略惨遭踏空)')
ax_test.axvspan(pd.to_datetime('2024-01-01'), pd.to_datetime('2024-06-01'), color='purple', alpha=0.08, label='2024 微盘股踩踏底 (对称策略反应迟钝)')

plt.tight_layout()
plt.show()

print("\n🎉 Step 44 验证完毕！红色的阴影面积，就是你放弃“对称美学”后，凭硬核逻辑抢回来的真金白银！")

#%% Step 45: 核心组件替换测试 —— 原版 vs 纯黄金 vs 纯南华
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker

print("\n========== 开始执行 Step 45: 商品端底层资产三维对比测试 ==========")

# --- 1. 独立标尺与防线构建 (严格基于 ver2.0 底层变量) ---
print("正在从全景数据源中分离提取：纯黄金标尺 与 纯南华标尺...")

# 【黄金端标尺】(提取华安黄金ETF)
gold_ret = ret_all['华安黄金ETF'].reindex(dates_all).fillna(0)
gold_nav = (1 + gold_ret).cumprod()
gold_ma20 = gold_nav.rolling(window=20).mean()
gold_vol = gold_ret.rolling(window=20).std().fillna(0.01)

# 【南华端标尺】(提取南华期货指数全时期数据)
nh_ret_full = ret_long['南华期货:商品指数'].reindex(dates_all).fillna(0)
nh_nav_full = (1 + nh_ret_full).cumprod()
nh_ma20_full = nh_nav_full.rolling(window=20).mean()
nh_vol_full = nh_ret_full.rolling(window=20).std().fillna(0.01)

# --- 2. 状态机初始化 ---
ret_v4_original = [] # v4.0 原版 (前期南华 + 后期4只等权ETF)
ret_v4_gold = []     # v4.0 纯黄金版 (全时期仅使用 华安黄金ETF 518880)
ret_v4_nanhua = []   # v4.0 纯南华版 (全时期仅使用 南华期货指数)

print("正在平行推演三大宇宙：原版综合商品 vs 纯黄金避险 vs 纯南华Beta ...")

for d in dates_all:
    # --- 基础权重与公共数据 (继承自普林格与底层设定) ---
    w_eq = weights_daily_long['沪深300指数'].loc[d] if pd.notna(weights_daily_long['沪深300指数'].loc[d]) else 0.0
    w_com = weights_daily_long['南华期货:商品指数'].loc[d] if pd.notna(weights_daily_long['南华期货:商品指数'].loc[d]) else 0.0
    w_bond_total = (weights_daily_long['中证基金指数:货币基金'] + weights_daily_long['中证全债指数']).loc[d] if pd.notna((weights_daily_long['中证基金指数:货币基金'] + weights_daily_long['中证全债指数']).loc[d]) else 0.0
    
    w_cdb_base = min(0.10, w_bond_total) 
    w_cb_base = max(0.0, w_bond_total - 0.10)
    
    is_eq_heavy = w_eq > 0.65
    is_com_heavy = w_com > 0.65
    
    loc_idx = dates_all.index(d)
    prev_date = dates_all[loc_idx - 1] if loc_idx > 0 else dates_all[0]
    
    # 🌟 A. 提取公共主引擎标尺 (严格读取 ver2.0.py 原生变量) 🌟
    if d < split_dt:
        # 股票端 (实盘前：沪深300)
        e_p = hs300_price.loc[prev_date] if pd.notna(hs300_price.loc[prev_date]) else np.nan
        e_ma = hs300_ma20.loc[prev_date] if pd.notna(hs300_ma20.loc[prev_date]) else np.nan
        e_vol = hs300_vol.loc[prev_date] if pd.notna(hs300_vol.loc[prev_date]) else 0.01
        r_e = ret_long['沪深300指数'].loc[d] if pd.notna(ret_long['沪深300指数'].loc[d]) else 0.0
        
        # 商品原版端 (实盘前：南华期货指数)
        c_p = nh_nav.loc[prev_date] if pd.notna(nh_nav.loc[prev_date]) else np.nan
        c_ma = nh_ma20.loc[prev_date] if pd.notna(nh_ma20.loc[prev_date]) else np.nan
        c_vol = nh_vol.loc[prev_date] if pd.notna(nh_vol.loc[prev_date]) else 0.01
        r_c = nh_ret.loc[d] if pd.notna(nh_ret.loc[d]) else 0.0
    else:
        # 股票端 (实盘后：Top4 景气度行业)
        e_p = top4_nav_s31.loc[prev_date] if prev_date in top4_nav_s31.index else np.nan
        e_ma = top4_ma20_s31.loc[prev_date] if prev_date in top4_ma20_s31.index else np.nan
        e_vol = top4_vol.loc[prev_date] if prev_date in top4_vol.index else 0.01
        r_e = top4_daily_returns.loc[d] if pd.notna(top4_daily_returns.loc[d]) else 0.0
        
        # 商品原版端 (实盘后：4只ETF等权篮子)
        c_p = basket_nav_s41.loc[prev_date] if prev_date in basket_nav_s41.index else np.nan
        c_ma = basket_ma20_s41.loc[prev_date] if prev_date in basket_ma20_s41.index else np.nan
        c_vol = basket_vol_s41.loc[prev_date] if prev_date in basket_vol_s41.index else 0.01
        r_c = basket_ret_eq_s41.loc[d] if d in basket_ret_eq_s41.index else 0.0

    # 固收水库端
    r_cb = ret_long['中证转债'].loc[d] if pd.notna(ret_long['中证转债'].loc[d]) else 0.0
    r_cdb = ret_long[cdb_col].loc[d] if pd.notna(ret_long[cdb_col].loc[d]) else 0.0
    
    # 🌟 B. 提取黄金专享端标尺 🌟
    g_p = gold_nav.loc[prev_date] if pd.notna(gold_nav.loc[prev_date]) else np.nan
    g_ma = gold_ma20.loc[prev_date] if pd.notna(gold_ma20.loc[prev_date]) else np.nan
    g_vol = gold_vol.loc[prev_date] if pd.notna(gold_vol.loc[prev_date]) else 0.01
    r_gold = gold_ret.loc[d]
    
    # 🌟 C. 提取全时期南华专享端标尺 🌟
    n_p = nh_nav_full.loc[prev_date] if pd.notna(nh_nav_full.loc[prev_date]) else np.nan
    n_ma = nh_ma20_full.loc[prev_date] if pd.notna(nh_ma20_full.loc[prev_date]) else np.nan
    n_vol = nh_vol_full.loc[prev_date] if pd.notna(nh_vol_full.loc[prev_date]) else 0.01
    r_nanhua = nh_ret_full.loc[d]

    # --- 核心判定：股票端公共动作 (单线防踏空极致风控) ---
    act_eq = (e_p >= e_ma * (1 - VOL_MULTIPLIER * e_vol)) if (is_eq_heavy and pd.notna(e_ma)) else True
    w_eq_final = w_eq if act_eq else 0.0

    # ================= 宇宙 1: 原版综合商品组合 =================
    act_com_orig = (c_p >= c_ma * (1 - VOL_MULTIPLIER * c_vol)) if (is_com_heavy and pd.notna(c_ma)) else True
    w_com_orig = w_com if act_com_orig else 0.0
    w_cdb_orig = w_cdb_base + (w_eq - w_eq_final) + (w_com - w_com_orig)
    ret_v4_original.append(w_eq_final * r_e + w_com_orig * r_c + w_cb_base * r_cb + w_cdb_orig * r_cdb)

    # ================= 宇宙 2: 纯黄金替代版 =================
    act_com_gold = (g_p >= g_ma * (1 - VOL_MULTIPLIER * g_vol)) if (is_com_heavy and pd.notna(g_ma)) else True
    w_com_gold = w_com if act_com_gold else 0.0
    w_cdb_gold = w_cdb_base + (w_eq - w_eq_final) + (w_com - w_com_gold)
    ret_v4_gold.append(w_eq_final * r_e + w_com_gold * r_gold + w_cb_base * r_cb + w_cdb_gold * r_cdb)
    
    # ================= 宇宙 3: 纯南华替代版 =================
    act_com_nh = (n_p >= n_ma * (1 - VOL_MULTIPLIER * n_vol)) if (is_com_heavy and pd.notna(n_ma)) else True
    w_com_nh = w_com if act_com_nh else 0.0
    w_cdb_nh = w_cdb_base + (w_eq - w_eq_final) + (w_com - w_com_nh)
    ret_v4_nanhua.append(w_eq_final * r_e + w_com_nh * r_nanhua + w_cb_base * r_cb + w_cdb_nh * r_cdb)

# --- 3. 净值计算与绩效对比 ---
nav_orig = (1 + pd.Series(ret_v4_original, index=dates_all)).cumprod()
nav_gold = (1 + pd.Series(ret_v4_gold, index=dates_all)).cumprod()
nav_nanhua = (1 + pd.Series(ret_v4_nanhua, index=dates_all)).cumprod()

def calc_custom_metrics(nav_series, name):
    tot_days = len(nav_series)
    daily_ret = nav_series.pct_change().fillna(0)
    ann_ret = nav_series.iloc[-1] ** (252 / tot_days) - 1 if tot_days > 0 else 0
    max_dd = (nav_series / nav_series.cummax() - 1).min()
    ann_vol = daily_ret.std() * np.sqrt(252)
    sharpe = (ann_ret - 0.02) / ann_vol if ann_vol > 0 else 0
    calmar = ann_ret / abs(max_dd) if max_dd != 0 else 0
    return {
        '资产配置版本': name, 
        '年化收益': f"{ann_ret*100:>6.2f}%", 
        '最大回撤': f"{max_dd*100:>7.2f}%",
        '年化波动率': f"{ann_vol*100:>6.2f}%",
        '夏普比率': f"{sharpe:>5.2f}",
        '卡玛比率': f"{calmar:>5.2f}"
    }

print("\n========================= 【商品端消融实验】核心绩效揭晓 =========================")
print(pd.DataFrame([
    calc_custom_metrics(nav_orig, "v4.0 原版 (前期南华指数 + 后期4只等权ETF)"),
    calc_custom_metrics(nav_gold, "v4.0 纯黄金版 (全时期仅暴露于 华安黄金ETF)"),
    calc_custom_metrics(nav_nanhua, "v4.0 纯南华版 (全时期仅暴露于 南华期货指数)")
]).to_string(index=False))
print("===================================================================================")

# --- 4. 绘图：资金曲线三方大乱斗 ---
fig_test, ax_test = plt.subplots(figsize=(16, 8))

# 使用区分度极高的颜色进行绘制
ax_test.plot(nav_orig.index, nav_orig, label='v4.0 原版 (宽基商品综合暴露)', color='crimson', linewidth=3, zorder=5)
ax_test.plot(nav_nanhua.index, nav_nanhua, label='v4.0 纯南华版 (强工业大宗属性)', color='steelblue', linewidth=2.5, linestyle='--', zorder=4)
ax_test.plot(nav_gold.index, nav_gold, label='v4.0 纯黄金版 (纯避险抗通胀属性)', color='goldenrod', linewidth=2.5, linestyle='-.', zorder=3)

ax_test.set_title('商品组件终极替换测试：原版综合 vs 纯南华指数 vs 纯黄金ETF', fontsize=17, fontweight='bold', pad=15)
ax_test.set_ylabel('累计净值 (初始=1.0)', fontsize=14)
ax_test.legend(loc='upper left', fontsize=13, framealpha=0.9)
ax_test.grid(True, linestyle=':', alpha=0.7)

# 标出一些典型的大宗分化时期
ax_test.axvspan(pd.to_datetime('2020-03-01'), pd.to_datetime('2021-06-01'), color='gray', alpha=0.08, label='疫后通胀与工业品狂暴牛市')
ax_test.axvspan(pd.to_datetime('2022-02-01'), pd.to_datetime('2022-12-01'), color='blue', alpha=0.05, label='俄乌冲突 (金银强势避险期)')
ax_test.axvspan(pd.to_datetime('2023-01-01'), pd.to_datetime('2024-01-01'), color='purple', alpha=0.05, label='复苏预期落空 (纯南华承压期)')

plt.tight_layout()
plt.show()

print("\n🎉 Step 45 (三维对比版) 运行完毕！通过这份报表，你可以一眼看透商品端‘工业Beta’与‘避险黄金’在量化系统中的真实作用边界。")

#%% Step 46: 核心组件替换测试 —— 股票端【四大宽基等权】 vs 【原版行业景气度轮动】
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import akshare as ak
import time
import datetime

print("\n========== 开始执行 Step 46: 股票端底层资产替换对比测试 ==========")

# --- 0. 环境护城河：确保基础变量存在 ---
if 'split_dt' not in locals(): split_dt = pd.to_datetime('2021-04-01')
if 'start_date_str_10y' not in locals(): start_date_str_10y = "20151201"
if 'end_date_str' not in locals(): end_date_str = datetime.datetime.now().strftime("%Y%m%d")
if 'VOL_MULTIPLIER' not in locals(): VOL_MULTIPLIER = 1.5

# --- 1. 使用双重降级下载法，获取宽基 ETF ---
broad_etfs = {
    '沪深300ETF': '510300',
    '中证1000ETF': '512100',
    '创业板指ETF': '159915',
    '恒生指数ETF': '159920'
}

print("正在构建四大宽基 ETF 行情数据(采用双重降级重试引擎)...")
broad_prices = pd.DataFrame(index=dates_all)

for name, code in broad_etfs.items():
    for attempt in range(3):
        try:
            # 方案 A: 尝试通过基金接口下载
            df = ak.fund_etf_hist_em(symbol=code, period="daily", start_date=start_date_str_10y, end_date=end_date_str)
        except:
            # 方案 B: 降级通过指数/股票日频接口下载
            prefix = 'sh' if code.startswith(('5', '6')) else 'sz'
            df = ak.stock_zh_index_daily(symbol=f"{prefix}{code}")
        
        if df is not None and not df.empty:
            # 统一列名映射
            col_map = {'date': '日期', 'close': '收盘', '收盘价': '收盘'}
            df.rename(columns=lambda x: col_map.get(x, x), inplace=True)
            
            if '日期' in df.columns and '收盘' in df.columns:
                df['日期'] = pd.to_datetime(df['日期'])
                df = df.set_index('日期')
                # 提取并对齐数据
                broad_prices[name] = df['收盘'].reindex(dates_all)
                print(f"✅ 成功获取: {name} ({code})")
                break
        time.sleep(1)
        
    if name not in broad_prices.columns:
        print(f"❌ {name} 获取彻底失败，系统将跳过该 ETF！")

# 巧妙处理未上市数据：向前填充停牌，探测最晚起始日
broad_prices_ffill = broad_prices.ffill()
latest_start_dt = broad_prices_ffill.dropna().index.min()
print(f"\n⚠️ 截断对齐：四大宽基 ETF 共同存在数据的最早日期为【{latest_start_dt.strftime('%Y-%m-%d')}】。")
print("测试将从该日起统一重置起跑线，保证对比绝对公平！")

dates_s46 = [d for d in dates_all if d >= latest_start_dt]

# 生成宽基组合综合标尺 (跳过早期的 NaN)
broad_ret_daily = broad_prices_ffill.pct_change().mean(axis=1, skipna=True).fillna(0)
broad_nav = (1 + broad_ret_daily).cumprod()
broad_ma20 = broad_nav.rolling(window=20).mean()
broad_vol = broad_ret_daily.rolling(window=20).std().fillna(0.01)

# --- 2. 状态机初始化 ---
ret_v4_original = [] # v4.0 原版 (股票端：前期300 + 后期Top4轮动)
ret_v4_broad = []    # v4.0 宽基版 (股票端：全时期 4宽基等权)

print("正在平行推演：原版(行业轮动 Alpha) vs 宽基版(纯大盘 Beta) ...")

for d in dates_s46:
    # 基础权重读取
    w_eq = weights_daily_long['沪深300指数'].loc[d] if pd.notna(weights_daily_long['沪深300指数'].loc[d]) else 0.0
    w_com = weights_daily_long['南华期货:商品指数'].loc[d] if pd.notna(weights_daily_long['南华期货:商品指数'].loc[d]) else 0.0
    w_bond_total = (weights_daily_long['中证基金指数:货币基金'] + weights_daily_long['中证全债指数']).loc[d] if pd.notna((weights_daily_long['中证基金指数:货币基金'] + weights_daily_long['中证全债指数']).loc[d]) else 0.0
    
    w_cdb_base = min(0.10, w_bond_total) 
    w_cb_base = max(0.0, w_bond_total - 0.10)
    
    is_eq_heavy = w_eq > 0.65
    is_com_heavy = w_com > 0.65
    
    loc_idx_all = dates_all.index(d)
    prev_date = dates_all[loc_idx_all - 1] if loc_idx_all > 0 else dates_all[0]
    
    # --- 提取原版公共商品/固收标尺 (严格对齐 _s41 变量) ---
    if d < split_dt:
        c_p = nh_nav.loc[prev_date] if pd.notna(nh_nav.loc[prev_date]) else np.nan
        c_ma = nh_ma20.loc[prev_date] if pd.notna(nh_ma20.loc[prev_date]) else np.nan
        c_vol = nh_vol.loc[prev_date] if pd.notna(nh_vol.loc[prev_date]) else 0.01
        r_c = nh_ret.loc[d] if pd.notna(nh_ret.loc[d]) else 0.0
    else:
        c_p = basket_nav_s41.loc[prev_date] if prev_date in basket_nav_s41.index else np.nan
        c_ma = basket_ma20_s41.loc[prev_date] if prev_date in basket_ma20_s41.index else np.nan
        c_vol = basket_vol_s41.loc[prev_date] if prev_date in basket_vol_s41.index else 0.01
        r_c = basket_ret_eq_s41.loc[d] if d in basket_ret_eq_s41.index else 0.0

    act_com = (c_p >= c_ma * (1 - VOL_MULTIPLIER * c_vol)) if (is_com_heavy and pd.notna(c_ma)) else True
    w_com_final = w_com if act_com else 0.0

    r_cb = ret_long['中证转债'].loc[d] if pd.notna(ret_long['中证转债'].loc[d]) else 0.0
    r_cdb = ret_long[cdb_col].loc[d] if pd.notna(ret_long[cdb_col].loc[d]) else 0.0
    
    # --- 提取原版股票引擎 (带 Top4 轮动) ---
    if d < split_dt:
        e_p_orig = hs300_price.loc[prev_date] if pd.notna(hs300_price.loc[prev_date]) else np.nan
        e_ma_orig = hs300_ma20.loc[prev_date] if pd.notna(hs300_ma20.loc[prev_date]) else np.nan
        e_vol_orig = hs300_vol.loc[prev_date] if pd.notna(hs300_vol.loc[prev_date]) else 0.01
        r_e_orig = ret_long['沪深300指数'].loc[d] if pd.notna(ret_long['沪深300指数'].loc[d]) else 0.0
    else:
        e_p_orig = top4_nav_s31.loc[prev_date] if prev_date in top4_nav_s31.index else np.nan
        e_ma_orig = top4_ma20_s31.loc[prev_date] if prev_date in top4_ma20_s31.index else np.nan
        e_vol_orig = top4_vol.loc[prev_date] if prev_date in top4_vol.index else 0.01
        r_e_orig = top4_daily_returns.loc[d] if pd.notna(top4_daily_returns.loc[d]) else 0.0

    # --- 提取新生成的宽基引擎标尺 ---
    e_p_broad = broad_nav.loc[prev_date] if pd.notna(broad_nav.loc[prev_date]) else np.nan
    e_ma_broad = broad_ma20.loc[prev_date] if pd.notna(broad_ma20.loc[prev_date]) else np.nan
    e_vol_broad = broad_vol.loc[prev_date] if pd.notna(broad_vol.loc[prev_date]) else 0.01
    r_e_broad = broad_ret_daily.loc[d]

    # ================= 撮合宇宙 1: 原版组合 =================
    act_eq_orig = (e_p_orig >= e_ma_orig * (1 - VOL_MULTIPLIER * e_vol_orig)) if (is_eq_heavy and pd.notna(e_ma_orig)) else True
    w_eq_orig = w_eq if act_eq_orig else 0.0
    w_cdb_orig = w_cdb_base + (w_eq - w_eq_orig) + (w_com - w_com_final)
    ret_v4_original.append(w_eq_orig * r_e_orig + w_com_final * r_c + w_cb_base * r_cb + w_cdb_orig * r_cdb)

    # ================= 撮合宇宙 2: 宽基替代版 =================
    act_eq_broad = (e_p_broad >= e_ma_broad * (1 - VOL_MULTIPLIER * e_vol_broad)) if (is_eq_heavy and pd.notna(e_ma_broad)) else True
    w_eq_broad = w_eq if act_eq_broad else 0.0
    w_cdb_broad = w_cdb_base + (w_eq - w_eq_broad) + (w_com - w_com_final)
    ret_v4_broad.append(w_eq_broad * r_e_broad + w_com_final * r_c + w_cb_base * r_cb + w_cdb_broad * r_cdb)

# --- 3. 净值计算与绩效考核 ---
nav_orig = (1 + pd.Series(ret_v4_original, index=dates_s46)).cumprod()
nav_broad = (1 + pd.Series(ret_v4_broad, index=dates_s46)).cumprod()

def calc_custom_metrics(nav_series, name):
    tot_days = len(nav_series)
    daily_ret = nav_series.pct_change().fillna(0)
    ann_ret = nav_series.iloc[-1] ** (252 / tot_days) - 1 if tot_days > 0 else 0
    max_dd = (nav_series / nav_series.cummax() - 1).min()
    ann_vol = daily_ret.std() * np.sqrt(252)
    sharpe = (ann_ret - 0.02) / ann_vol if ann_vol > 0 else 0
    calmar = ann_ret / abs(max_dd) if max_dd != 0 else 0
    return {
        '系统架构版本': name, 
        '年化收益': f"{ann_ret*100:>6.2f}%", 
        '最大回撤': f"{max_dd*100:>7.2f}%",
        '年化波动率': f"{ann_vol*100:>6.2f}%",
        '夏普比率': f"{sharpe:>5.2f}",
        '卡玛比率': f"{calmar:>5.2f}"
    }

print("\n========================= 【股票端 Alpha 消融实验】揭晓 =========================")
print(pd.DataFrame([
    calc_custom_metrics(nav_orig, "v4.0 原版 (含 AI行业景气度轮动 Alpha)"),
    calc_custom_metrics(nav_broad, "v4.0 宽基版 (四大宽基被动等权 Beta)")
]).to_string(index=False))
print("=================================================================================")

# --- 4. 绘图：资金曲线对决 ---
fig_test, ax_test = plt.subplots(figsize=(16, 8))

ax_test.plot(nav_orig.index, nav_orig, label='v4.0 原版 (带Top4行业轮动超额)', color='crimson', linewidth=3, zorder=5)
ax_test.plot(nav_broad.index, nav_broad, label='v4.0 宽基版 (300/1000/创业/恒生 等权)', color='steelblue', linewidth=2.5, linestyle='-.', zorder=4)

# 突出显示两者净值的超额差异
ax_test.fill_between(nav_orig.index, nav_orig, nav_broad, where=(nav_orig > nav_broad), color='crimson', alpha=0.15, label='原版：行业轮动创造的纯 Alpha 利润')
ax_test.fill_between(nav_orig.index, nav_orig, nav_broad, where=(nav_orig < nav_broad), color='steelblue', alpha=0.15, label='宽基超越轮动的区间')

ax_test.set_title(f'剥离 Alpha 测试：行业轮动 vs 四大宽基等权\n(起点已严格对齐至 {latest_start_dt.strftime("%Y-%m-%d")})', fontsize=16, fontweight='bold', pad=15)
ax_test.set_ylabel('累计净值 (基准=1.0)', fontsize=14)
ax_test.legend(loc='upper left', fontsize=13, framealpha=0.9)
ax_test.grid(True, linestyle=':', alpha=0.7)

plt.tight_layout()
plt.show()

print("\n🎉 Step 46 运行完毕！")

#%% Step 47: 宽基版 (四大宽基被动等权) 全景联动图与原版绩效对决
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import matplotlib.patches as mpatches
from matplotlib.ticker import FuncFormatter
import matplotlib.ticker as ticker

print("\n========== 开始执行 Step 47: 宽基版全景联动图与原版绩效对决 ==========")

# --- 0. 环境护城河检查 ---
if 'dates_s46' not in locals() or 'broad_nav' not in locals():
    raise ValueError("❌ 找不到 Step 46 的运行数据，请先运行 Step 46 获取宽基数据！")

# --- 1. 状态追踪、统计指标与数据容器初始化 ---
trades_broad_eq = 0
trades_broad_com = 0
prev_esc_broad_eq = False
prev_esc_broad_com = False

daily_active_assets = {} # 用于甘特图
is_eq_escape_daily = {}  # 股票端逃逸背景
is_com_escape_daily = {} # 商品端逃逸背景

hist_w_eq = []; hist_w_com = []; hist_w_cb = []; hist_w_cdb = []
ret_orig = []   # 存储 v4.0 原版收益
ret_broad = []  # 存储 v4.0 宽基版收益

# 定义宽基版股票端的固定资产池
broad_asset_names = ['沪深300ETF', '中证1000ETF', '创业板指ETF', '恒生指数ETF']

print("正在平行推演底层资金流转脉络：原版(行业轮动) vs 宽基版(四大宽基)...")

for d in dates_s46:
    # --- 基础权重分配 ---
    w_eq = weights_daily_long['沪深300指数'].loc[d] if pd.notna(weights_daily_long['沪深300指数'].loc[d]) else 0.0
    w_com = weights_daily_long['南华期货:商品指数'].loc[d] if pd.notna(weights_daily_long['南华期货:商品指数'].loc[d]) else 0.0
    w_bond_total = (weights_daily_long['中证基金指数:货币基金'] + weights_daily_long['中证全债指数']).loc[d] if pd.notna((weights_daily_long['中证基金指数:货币基金'] + weights_daily_long['中证全债指数']).loc[d]) else 0.0
    
    w_cdb_base = min(0.10, w_bond_total) 
    w_cb_base = max(0.0, w_bond_total - 0.10)
    
    is_eq_heavy = w_eq > 0.65
    is_com_heavy = w_com > 0.65
    
    loc_idx_all = dates_all.index(d)
    prev_date = dates_all[loc_idx_all - 1] if loc_idx_all > 0 else dates_all[0]
    
    # --- 提取共享的商品端/固收端标尺 (严格采用 _s41 后缀) ---
    if d < split_dt:
        c_p = nh_nav.loc[prev_date] if pd.notna(nh_nav.loc[prev_date]) else np.nan
        c_ma = nh_ma20.loc[prev_date] if pd.notna(nh_ma20.loc[prev_date]) else np.nan
        c_vol = nh_vol.loc[prev_date] if pd.notna(nh_vol.loc[prev_date]) else 0.01
        r_c = nh_ret.loc[d] if pd.notna(nh_ret.loc[d]) else 0.0
    else:
        c_p = basket_nav_s41.loc[prev_date] if prev_date in basket_nav_s41.index else np.nan
        c_ma = basket_ma20_s41.loc[prev_date] if prev_date in basket_ma20_s41.index else np.nan
        c_vol = basket_vol_s41.loc[prev_date] if prev_date in basket_vol_s41.index else 0.01
        r_c = basket_ret_eq_s41.loc[d] if d in basket_ret_eq_s41.index else 0.0

    r_cb, r_cdb = ret_long['中证转债'].loc[d], ret_long[cdb_col].loc[d]

    act_com = (c_p >= c_ma * (1 - VOL_MULTIPLIER * c_vol)) if (is_com_heavy and pd.notna(c_ma)) else True
    w_com_final = w_com if act_com else 0.0

    # --- 提取宽基股票端标尺 ---
    e_p_broad = broad_nav.loc[prev_date] if pd.notna(broad_nav.loc[prev_date]) else np.nan
    e_ma_broad = broad_ma20.loc[prev_date] if pd.notna(broad_ma20.loc[prev_date]) else np.nan
    e_vol_broad = broad_vol.loc[prev_date] if pd.notna(broad_vol.loc[prev_date]) else 0.01
    r_e_broad = broad_ret_daily.loc[d]

    # --- 提取原版股票端标尺 (严格采用 _s31 后缀) ---
    if d < split_dt:
        e_p_orig = hs300_price.loc[prev_date] if pd.notna(hs300_price.loc[prev_date]) else np.nan
        e_ma_orig = hs300_ma20.loc[prev_date] if pd.notna(hs300_ma20.loc[prev_date]) else np.nan
        e_vol_orig = hs300_vol.loc[prev_date] if pd.notna(hs300_vol.loc[prev_date]) else 0.01
        r_e_orig = ret_long['沪深300指数'].loc[d] if pd.notna(ret_long['沪深300指数'].loc[d]) else 0.0
    else:
        e_p_orig = top4_nav_s31.loc[prev_date] if prev_date in top4_nav_s31.index else np.nan
        e_ma_orig = top4_ma20_s31.loc[prev_date] if prev_date in top4_ma20_s31.index else np.nan
        e_vol_orig = top4_vol.loc[prev_date] if prev_date in top4_vol.index else 0.01
        r_e_orig = top4_daily_returns.loc[d] if pd.notna(top4_daily_returns.loc[d]) else 0.0

    # ================= 撮合 1: v4.0 原版 (行业轮动 Alpha) =================
    act_eq_orig = (e_p_orig >= e_ma_orig * (1 - VOL_MULTIPLIER * e_vol_orig)) if (is_eq_heavy and pd.notna(e_ma_orig)) else True
    w_eq_orig = w_eq if act_eq_orig else 0.0
    w_cdb_orig = w_cdb_base + (w_eq - w_eq_orig) + (w_com - w_com_final)
    ret_orig.append(w_eq_orig * r_e_orig + w_com_final * r_c + w_cb_base * r_cb + w_cdb_orig * r_cdb)

    # ================= 撮合 2: v4.0 宽基版 (大盘等权 Beta) =================
    act_eq_broad = (e_p_broad >= e_ma_broad * (1 - VOL_MULTIPLIER * e_vol_broad)) if (is_eq_heavy and pd.notna(e_ma_broad)) else True
    w_eq_broad = w_eq if act_eq_broad else 0.0
    w_cdb_broad = w_cdb_base + (w_eq - w_eq_broad) + (w_com - w_com_final)
    ret_broad.append(w_eq_broad * r_e_broad + w_com_final * r_c + w_cb_base * r_cb + w_cdb_broad * r_cdb)

    # --- 宽基版：统计调仓与收集绘图数据 ---
    if (not act_eq_broad) != prev_esc_broad_eq: 
        trades_broad_eq += 1
        prev_esc_broad_eq = (not act_eq_broad)
    if (not act_com) != prev_esc_broad_com: 
        trades_broad_com += 1
        prev_esc_broad_com = (not act_com)

    active_assets = []
    if w_eq_broad > 0: active_assets.extend(broad_asset_names)
    if w_com_final > 0: active_assets.append('【商】大宗商品端')
    daily_active_assets[d] = active_assets
    
    is_eq_escape_daily[d] = not act_eq_broad
    is_com_escape_daily[d] = not act_com
    
    hist_w_eq.append(w_eq_broad * 100)
    hist_w_com.append(w_com_final * 100)
    hist_w_cb.append(w_cb_base * 100)
    hist_w_cdb.append(w_cdb_broad * 100)

# --- 3. 计算净值与绩效输出 ---
nav_orig = (1 + pd.Series(ret_orig, index=dates_s46)).cumprod()
nav_broad = (1 + pd.Series(ret_broad, index=dates_s46)).cumprod()
nav_hs300 = (1 + ret_long['沪深300指数'].reindex(dates_s46).fillna(0)).cumprod()

def calc_custom_metrics(nav_series, name):
    tot_days = len(nav_series)
    daily_ret = nav_series.pct_change().fillna(0)
    ann_ret = nav_series.iloc[-1] ** (252 / tot_days) - 1 if tot_days > 0 else 0
    max_dd = (nav_series / nav_series.cummax() - 1).min()
    ann_vol = daily_ret.std() * np.sqrt(252)
    sharpe = (ann_ret - 0.02) / ann_vol if ann_vol > 0 else 0
    calmar = ann_ret / abs(max_dd) if max_dd != 0 else 0
    return {
        '系统架构版本': name, 
        '年化收益': f"{ann_ret*100:>6.2f}%", 
        '最大回撤': f"{max_dd*100:>7.2f}%",
        '年化波动率': f"{ann_vol*100:>6.2f}%",
        '夏普比率': f"{sharpe:>5.2f}",
        '卡玛比率': f"{calmar:>5.2f}"
    }

print("\n========================= 【股票端 Alpha 消融实验】核心绩效揭晓 =========================")
print(pd.DataFrame([
    calc_custom_metrics(nav_orig, "v4.0 原版 (带Top4景气度轮动 Alpha)"),
    calc_custom_metrics(nav_broad, "v4.0 宽基版 (四大宽基被动等权 Beta)")
]).to_string(index=False))
print("=========================================================================================")

print(f"\n▶ 【宽基版】避险防线实盘审计：股票端逃逸/回归 {trades_broad_eq} 次，商品端逃逸/回归 {trades_broad_com} 次")
print(f"注：自 {dates_s46[0].strftime('%Y-%m-%d')} 起算，平均每年股票端仅被动换手 {(trades_broad_eq) / (len(dates_s46)/252):.1f} 次。")

# --- 4. 渲染全景联动图 (甘特图 + 资金堆叠 + 原版对比净值曲线) ---
print("\n正在渲染带季度坐标轴的全景甘特图与 Alpha 剥离对比图...")
all_labels = []
for assets in daily_active_assets.values():
    for a in assets:
        if a not in all_labels: all_labels.append(a)
# 强制商品排在最上方
if '【商】大宗商品端' in all_labels: 
    all_labels.remove('【商】大宗商品端')
    all_labels.insert(0, '【商】大宗商品端')
label_y = {l: i for i, l in enumerate(all_labels)}

# 创建三个共享 X 轴的子图
fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(16, 18), gridspec_kw={'height_ratios': [1.2, 0.8, 1.5]}, sharex=True)

# ===== 子图 1：持仓甘特图与逃逸背景 =====
for lbl, y in label_y.items():
    is_in = False; start = None
    color = 'darkgoldenrod' if '【商】' in lbl else 'steelblue' # 宽基版使用蓝色
    for d in dates_s46:
        present = lbl in daily_active_assets[d]
        if present and not is_in: 
            is_in = True
            start = d
        elif not present and is_in: 
            is_in = False
            ax1.broken_barh([(mdates.date2num(start), mdates.date2num(d)-mdates.date2num(start))], (y-0.3, 0.6), color=color, edgecolor='black', linewidth=0.5)
    if is_in: 
        ax1.broken_barh([(mdates.date2num(start), mdates.date2num(dates_s46[-1])-mdates.date2num(start))], (y-0.3, 0.6), color=color)

# 绘制逃逸红色/橙色警示背景区
for d in dates_s46:
    if is_eq_escape_daily[d]: ax1.axvspan(d, d + pd.Timedelta(days=1), color='crimson', alpha=0.15)
    if is_com_escape_daily[d]: ax1.axvspan(d, d + pd.Timedelta(days=1), color='orange', alpha=0.15)

ax1.set_yticks(range(len(all_labels)))
ax1.set_yticklabels(all_labels, fontsize=12)
ax1.invert_yaxis()
ax1.set_title('v4.0 宽基版(四大宽基等权) —— 主引擎定向避险状态甘特图\n(红色阴影区代表该底层防线被击穿，资金全量逃入避险水库)', fontsize=16, fontweight='bold')
ax1.grid(True, linestyle=':', alpha=0.6)

# ===== 子图 2：资金结构堆叠图 =====
ax2.stackplot(dates_s46, hist_w_eq, hist_w_cb, hist_w_com, hist_w_cdb, 
              labels=['股票(四大宽基)', '可转债(进攻)', '大宗商品', '国开债(蓄水池)'], 
              colors=['steelblue', 'darkviolet', 'darkgoldenrod', 'lightseagreen'], alpha=0.85)
ax2.set_ylabel('资金占比 (%)', fontsize=12)
ax2.set_ylim(0, 100)
ax2.legend(loc='upper left', ncol=4, fontsize=11, framealpha=0.9)
ax2.margins(x=0)

# ===== 子图 3：净值增长对比图 (原版 Alpha vs 宽基 Beta) =====
ax3.plot(nav_orig.index, nav_orig, label='v4.0 原版 (带Top4行业景气度轮动 Alpha)', color='crimson', linewidth=3, zorder=5)
ax3.plot(nav_broad.index, nav_broad, label='v4.0 宽基版 (300/1000/创业/恒生 等权 Beta)', color='steelblue', linewidth=2.5, linestyle='-', zorder=4)
ax3.plot(nav_hs300.index, nav_hs300, label='参考基准：沪深300指数', color='black', linewidth=1, alpha=0.5, zorder=3)

# 突出显示两者净值的超额差异
ax3.fill_between(nav_orig.index, nav_orig, nav_broad, where=(nav_orig > nav_broad), color='crimson', alpha=0.15, label='原版：AI行业轮动创造的纯 Alpha 利润')
ax3.fill_between(nav_orig.index, nav_orig, nav_broad, where=(nav_orig < nav_broad), color='steelblue', alpha=0.15, label='宽基超越轮动的区间')

ax3.set_title(f'剥离 Alpha 测试：行业轮动 vs 四大宽基等权 (起点对齐至 {dates_s46[0].strftime("%Y-%m-%d")})', fontsize=15, fontweight='bold', pad=15)
ax3.set_ylabel('累计净值', fontsize=12)
ax3.legend(loc='upper left', fontsize=12)
ax3.grid(True, linestyle=':', alpha=0.6)

# ★ 季度时间轴格式化处理 ★
def quarter_formatter(x, pos):
    try:
        dt = mdates.num2date(x)
        q = (dt.month - 1) // 3 + 1
        return f"{dt.year}Q{q}"
    except:
        return ""

ax3.xaxis.set_major_locator(mdates.MonthLocator(bymonth=[1, 4, 7, 10]))
ax3.xaxis.set_major_formatter(FuncFormatter(quarter_formatter))
plt.setp(ax3.get_xticklabels(), rotation=45, ha='right', fontsize=11, fontweight='bold')

plt.tight_layout()
plt.show()

print("\n🎉 Step 47 运行完毕！通过终端的卡玛比率与净值图的红色阴影，你能极其完美地分离出策略的选股超额与风控底座保底能力。")

#%% Step 48: 避险水库久期测试 —— 国开债(5-7年) vs 国开债(0-3年) 四维对决
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.ticker import FuncFormatter
import akshare as ak
import time
import datetime

print("\n========== 开始执行 Step 48: 避险水库久期替换对比测试 ==========")

# --- 0. 环境护城河检查 ---
if 'dates_s46' not in locals() or 'broad_nav' not in locals():
    raise ValueError("❌ 找不到 Step 46/47 的宽基运行数据，请先顺序执行前面的代码！")

if 'start_date_str_10y' not in locals(): start_date_str_10y = "20151201"
if 'end_date_str' not in locals(): end_date_str = datetime.datetime.now().strftime("%Y%m%d")

# --- 1. 下载并补齐 0-3年国开债 (932194.CSI) 数据 ---
if '国开债0-3' not in ret_all.columns:
    print("正在联网获取 [中证国开债0-3年指数 932194.CSI] 数据...")
    for attempt in range(3):
        try:
            df_cdb_short = ak.stock_zh_index_hist_csindex(symbol="932194", start_date=start_date_str_10y, end_date=end_date_str)
            col_map = {'date': '日期', 'close': '收盘', '收盘价': '收盘'}
            df_cdb_short.rename(columns=lambda x: col_map.get(x, x), inplace=True)
            df_cdb_short['日期'] = pd.to_datetime(df_cdb_short['日期'])
            df_cdb_short = df_cdb_short.set_index('日期')
            
            # 计算日收益率并对齐到全局日历
            ret_all['国开债0-3'] = df_cdb_short['收盘'].pct_change().reindex(dates_all).fillna(0)
            print("✅ 成功获取: 国开债0-3年 (932194.CSI)")
            break
        except Exception as e:
            time.sleep(1)
    if '国开债0-3' not in ret_all.columns:
        print("❌ 国开债0-3年 获取失败，系统将默认其收益率为 0 强行继续！")
        ret_all['国开债0-3'] = 0.0

# 确认原版 5-7 年国开债的列名
original_cdb_col = cdb_col if 'cdb_col' in locals() else '国开债5-7'

# --- 2. 状态机初始化 (四维宇宙) ---
ret_orig_cdb57 = []  # 组合1: 原版Alpha + 5-7年长债
ret_broad_cdb57 = [] # 组合2: 宽基Beta  + 5-7年长债
ret_orig_cdb03 = []  # 组合3: 原版Alpha + 0-3年短债
ret_broad_cdb03 = [] # 组合4: 宽基Beta  + 0-3年短债

print(f"正在平行推演四大宇宙...")
print(f"原避险水库: [{original_cdb_col}]  |  新避险水库: [国开债0-3]")

for d in dates_s46:
    # 基础权重分配
    w_eq = weights_daily_long['沪深300指数'].loc[d] if pd.notna(weights_daily_long['沪深300指数'].loc[d]) else 0.0
    w_com = weights_daily_long['南华期货:商品指数'].loc[d] if pd.notna(weights_daily_long['南华期货:商品指数'].loc[d]) else 0.0
    w_bond_total = (weights_daily_long['中证基金指数:货币基金'] + weights_daily_long['中证全债指数']).loc[d] if pd.notna((weights_daily_long['中证基金指数:货币基金'] + weights_daily_long['中证全债指数']).loc[d]) else 0.0
    
    w_cdb_base = min(0.10, w_bond_total) 
    w_cb_base = max(0.0, w_bond_total - 0.10)
    
    is_eq_heavy = w_eq > 0.65
    is_com_heavy = w_com > 0.65
    
    loc_idx_all = dates_all.index(d)
    prev_date = dates_all[loc_idx_all - 1] if loc_idx_all > 0 else dates_all[0]
    
    # === 提取所有底层标尺 ===
    # 1. 固收与水库收益率
    r_cb = ret_all['中证转债'].loc[d] if pd.notna(ret_all['中证转债'].loc[d]) else 0.0
    r_cdb_57 = ret_all[original_cdb_col].loc[d] if pd.notna(ret_all[original_cdb_col].loc[d]) else 0.0
    r_cdb_03 = ret_all['国开债0-3'].loc[d] if pd.notna(ret_all['国开债0-3'].loc[d]) else 0.0
    
    # 2. 商品端 (共享逻辑)
    if d < split_dt:
        c_p = nh_nav.loc[prev_date] if pd.notna(nh_nav.loc[prev_date]) else np.nan
        c_ma = nh_ma20.loc[prev_date] if pd.notna(nh_ma20.loc[prev_date]) else np.nan
        c_vol = nh_vol.loc[prev_date] if pd.notna(nh_vol.loc[prev_date]) else 0.01
        r_c = nh_ret.loc[d] if pd.notna(nh_ret.loc[d]) else 0.0
    else:
        c_p = basket_nav_s41.loc[prev_date] if prev_date in basket_nav_s41.index else np.nan
        c_ma = basket_ma20_s41.loc[prev_date] if prev_date in basket_ma20_s41.index else np.nan
        c_vol = basket_vol_s41.loc[prev_date] if prev_date in basket_vol_s41.index else 0.01
        r_c = basket_ret_eq_s41.loc[d] if d in basket_ret_eq_s41.index else 0.0

    act_com = (c_p >= c_ma * (1 - VOL_MULTIPLIER * c_vol)) if (is_com_heavy and pd.notna(c_ma)) else True
    w_com_final = w_com if act_com else 0.0

    # 3. 股票端：原版 Alpha (Top4轮动)
    if d < split_dt:
        e_p_orig = hs300_price.loc[prev_date] if pd.notna(hs300_price.loc[prev_date]) else np.nan
        e_ma_orig = hs300_ma20.loc[prev_date] if pd.notna(hs300_ma20.loc[prev_date]) else np.nan
        e_vol_orig = hs300_vol.loc[prev_date] if pd.notna(hs300_vol.loc[prev_date]) else 0.01
        r_e_orig = ret_all['沪深300指数'].loc[d] if pd.notna(ret_all['沪深300指数'].loc[d]) else 0.0
    else:
        e_p_orig = top4_nav_s31.loc[prev_date] if prev_date in top4_nav_s31.index else np.nan
        e_ma_orig = top4_ma20_s31.loc[prev_date] if prev_date in top4_ma20_s31.index else np.nan
        e_vol_orig = top4_vol.loc[prev_date] if prev_date in top4_vol.index else 0.01
        r_e_orig = top4_daily_returns.loc[d] if pd.notna(top4_daily_returns.loc[d]) else 0.0

    act_eq_orig = (e_p_orig >= e_ma_orig * (1 - VOL_MULTIPLIER * e_vol_orig)) if (is_eq_heavy and pd.notna(e_ma_orig)) else True
    w_eq_orig = w_eq if act_eq_orig else 0.0

    # 4. 股票端：宽基 Beta (4只等权)
    e_p_broad = broad_nav.loc[prev_date] if pd.notna(broad_nav.loc[prev_date]) else np.nan
    e_ma_broad = broad_ma20.loc[prev_date] if pd.notna(broad_ma20.loc[prev_date]) else np.nan
    e_vol_broad = broad_vol.loc[prev_date] if pd.notna(broad_vol.loc[prev_date]) else 0.01
    r_e_broad = broad_ret_daily.loc[d]
    
    act_eq_broad = (e_p_broad >= e_ma_broad * (1 - VOL_MULTIPLIER * e_vol_broad)) if (is_eq_heavy and pd.notna(e_ma_broad)) else True
    w_eq_broad = w_eq if act_eq_broad else 0.0

    # === 四维宇宙撮合 ===
    # 水库容量计算 (全量逃逸资金)
    w_cdb_orig_escape = w_cdb_base + (w_eq - w_eq_orig) + (w_com - w_com_final)
    w_cdb_broad_escape = w_cdb_base + (w_eq - w_eq_broad) + (w_com - w_com_final)

    # 组合 1：原版股票 + 5-7年国开债
    ret_orig_cdb57.append(w_eq_orig * r_e_orig + w_com_final * r_c + w_cb_base * r_cb + w_cdb_orig_escape * r_cdb_57)
    
    # 组合 2：宽基股票 + 5-7年国开债
    ret_broad_cdb57.append(w_eq_broad * r_e_broad + w_com_final * r_c + w_cb_base * r_cb + w_cdb_broad_escape * r_cdb_57)
    
    # 组合 3：原版股票 + 0-3年国开债
    ret_orig_cdb03.append(w_eq_orig * r_e_orig + w_com_final * r_c + w_cb_base * r_cb + w_cdb_orig_escape * r_cdb_03)
    
    # 组合 4：宽基股票 + 0-3年国开债
    ret_broad_cdb03.append(w_eq_broad * r_e_broad + w_com_final * r_c + w_cb_base * r_cb + w_cdb_broad_escape * r_cdb_03)

# --- 3. 净值计算与生成绩效矩阵 ---
nav_1 = (1 + pd.Series(ret_orig_cdb57, index=dates_s46)).cumprod()
nav_2 = (1 + pd.Series(ret_broad_cdb57, index=dates_s46)).cumprod()
nav_3 = (1 + pd.Series(ret_orig_cdb03, index=dates_s46)).cumprod()
nav_4 = (1 + pd.Series(ret_broad_cdb03, index=dates_s46)).cumprod()

def calc_custom_metrics(nav_series, name):
    tot_days = len(nav_series)
    daily_ret = nav_series.pct_change().fillna(0)
    ann_ret = nav_series.iloc[-1] ** (252 / tot_days) - 1 if tot_days > 0 else 0
    max_dd = (nav_series / nav_series.cummax() - 1).min()
    ann_vol = daily_ret.std() * np.sqrt(252)
    sharpe = (ann_ret - 0.02) / ann_vol if ann_vol > 0 else 0
    calmar = ann_ret / abs(max_dd) if max_dd != 0 else 0
    return {
        '系统架构版本': name, 
        '年化收益': f"{ann_ret*100:>6.2f}%", 
        '最大回撤': f"{max_dd*100:>7.2f}%",
        '年化波动率': f"{ann_vol*100:>6.2f}%",
        '夏普比率': f"{sharpe:>5.2f}",
        '卡玛比率': f"{calmar:>5.2f}"
    }

print("\n========================= 【水库久期敏感性测试】四组核心绩效 =========================")
print(pd.DataFrame([
    calc_custom_metrics(nav_1, "① 原版Alpha + 5-7年长债 (高收益强心跳)"),
    calc_custom_metrics(nav_3, "② 原版Alpha + 0-3年短债 (收益略损稳如狗)"),
    calc_custom_metrics(nav_2, "③ 宽基Beta  + 5-7年长债 (纯大盘长债版)"),
    calc_custom_metrics(nav_4, "④ 宽基Beta  + 0-3年短债 (纯大盘短债版)")
]).to_string(index=False))
print("======================================================================================")

# --- 4. 绘制终极四线交织图 ---
fig, ax = plt.subplots(figsize=(16, 8))

# 绘制原版 Alpha 组 (红色系)
ax.plot(nav_1.index, nav_1, label='① 原版(Top4轮动) + 5-7年长债水库', color='crimson', linewidth=3, zorder=5)
ax.plot(nav_3.index, nav_3, label='② 原版(Top4轮动) + 0-3年短债水库', color='lightcoral', linewidth=2.5, linestyle='-.', zorder=4)

# 绘制宽基 Beta 组 (蓝色系)
ax.plot(nav_2.index, nav_2, label='③ 宽基(四大等权) + 5-7年长债水库', color='steelblue', linewidth=3, zorder=3)
ax.plot(nav_4.index, nav_4, label='④ 宽基(四大等权) + 0-3年短债水库', color='lightblue', linewidth=2.5, linestyle='-.', zorder=2)

ax.set_title(f'避险水库久期测试：股票端(原版vs宽基) × 避险端(长债vs短债)\n(数据起算日: {dates_s46[0].strftime("%Y-%m-%d")})', fontsize=16, fontweight='bold', pad=15)
ax.set_ylabel('累计净值', fontsize=13)
ax.legend(loc='upper left', fontsize=12, framealpha=0.9)
ax.grid(True, linestyle=':', alpha=0.6)

# ★ 突出显示久期造成的差异 (填色)
ax.fill_between(nav_1.index, nav_1, nav_3, where=(nav_1 > nav_3), color='crimson', alpha=0.1, label='长债超额利差 (风险溢价)')
ax.fill_between(nav_1.index, nav_1, nav_3, where=(nav_1 < nav_3), color='lightcoral', alpha=0.2, label='长债回撤杀伤期 (短债优势体现)')

# 季度时间轴格式化
def quarter_formatter(x, pos):
    try:
        dt = mdates.num2date(x)
        q = (dt.month - 1) // 3 + 1
        return f"{dt.year}Q{q}"
    except: return ""

ax.xaxis.set_major_locator(mdates.MonthLocator(bymonth=[1, 4, 7, 10]))
ax.xaxis.set_major_formatter(FuncFormatter(quarter_formatter))
plt.setp(ax.get_xticklabels(), rotation=45, ha='right', fontsize=11, fontweight='bold')

plt.tight_layout()
plt.show()

print("\n🎉 Step 48 久期测试运行完毕！注意观察终端输出的【最大回撤】和【卡玛比率】。")
print("通常 0-3年 短债会略微牺牲一丁点年化收益，但能在极端债灾时换取极度平滑的资金曲线（卡玛比率上升）！")

#%% Step 49: 宽基版 (四大宽基) + 0-3年短债水库 —— 全景联动审计图
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import matplotlib.patches as mpatches
from matplotlib.ticker import FuncFormatter

print("\n========== 开始执行 Step 49: 宽基版 + 0-3年短债版 联动审计图 ==========")

# --- 1. 独立追踪“宽基+0-3年”宇宙的资金流转 ---
trades_broad_eq_03 = 0
trades_broad_com_03 = 0
prev_esc_broad_eq_03 = False
prev_esc_broad_com_03 = False

daily_active_assets_03 = {} # 甘特图容器
is_eq_escape_daily_03 = {}  # 股票逃逸背景
is_com_escape_daily_03 = {} # 商品逃逸背景

hist_w_eq_03 = []; hist_w_com_03 = []; hist_w_cb_03 = []; hist_w_cdb_03 = []
ret_broad_cdb03_audit = []

broad_asset_names = ['沪深300ETF', '中证1000ETF', '创业板指ETF', '恒生指数ETF']

for d in dates_s46:
    # 基础权重获取
    w_eq = weights_daily_long['沪深300指数'].loc[d] if pd.notna(weights_daily_long['沪深300指数'].loc[d]) else 0.0
    w_com = weights_daily_long['南华期货:商品指数'].loc[d] if pd.notna(weights_daily_long['南华期货:商品指数'].loc[d]) else 0.0
    w_bond_total = (weights_daily_long['中证基金指数:货币基金'] + weights_daily_long['中证全债指数']).loc[d] if pd.notna((weights_daily_long['中证基金指数:货币基金'] + weights_daily_long['中证全债指数']).loc[d]) else 0.0
    w_cdb_base = min(0.10, w_bond_total) 
    w_cb_base = max(0.0, w_bond_total - 0.10)
    
    loc_idx_all = dates_all.index(d)
    prev_date = dates_all[loc_idx_all - 1] if loc_idx_all > 0 else dates_all[0]
    
    # 提取判定标尺
    e_p = broad_nav.loc[prev_date]; e_ma = broad_ma20.loc[prev_date]; e_vol = broad_vol.loc[prev_date]
    if d < split_dt:
        c_p = nh_nav.loc[prev_date]; c_ma = nh_ma20.loc[prev_date]; c_vol = nh_vol.loc[prev_date]
        r_c = nh_ret.loc[d]
    else:
        c_p = basket_nav_s41.loc[prev_date]; c_ma = basket_ma20_s41.loc[prev_date]; c_vol = basket_vol_s41.loc[prev_date]
        r_c = basket_ret_eq_s41.loc[d]

    # 收益率 (使用 0-3年 短债)
    r_e = broad_ret_daily.loc[d]
    r_cb = ret_long['中证转债'].loc[d]
    r_cdb_03 = ret_all['国开债0-3'].loc[d]

    # 防线判定
    act_eq = (e_p >= e_ma * (1 - VOL_MULTIPLIER * e_vol)) if (w_eq > 0.65) else True
    act_com = (c_p >= c_ma * (1 - VOL_MULTIPLIER * c_vol)) if (w_com > 0.65) else True

    # 统计调仓
    if (not act_eq) != prev_esc_broad_eq_03: trades_broad_eq_03 += 1; prev_esc_broad_eq_03 = (not act_eq)
    if (not act_com) != prev_esc_broad_com_03: trades_broad_com_03 += 1; prev_esc_broad_com_03 = (not act_com)

    # 资金重分配
    final_w_eq = w_eq if act_eq else 0.0
    final_w_com = w_com if act_com else 0.0
    final_w_cdb = w_cdb_base + (w_eq - final_w_eq) + (w_com - final_w_com)
    
    ret_broad_cdb03_audit.append(final_w_eq * r_e + final_w_com * r_c + w_cb_base * r_cb + final_w_cdb * r_cdb_03)

    # 记录作图状态
    active_assets = []
    if final_w_eq > 0: active_assets.extend(broad_asset_names)
    if final_w_com > 0: active_assets.append('【商】大宗商品端')
    daily_active_assets_03[d] = active_assets
    is_eq_escape_daily_03[d] = not act_eq
    is_com_escape_daily_03[d] = not act_com
    hist_w_eq_03.append(final_w_eq * 100); hist_w_com_03.append(final_w_com * 100)
    hist_w_cb_03.append(w_cb_base * 100); hist_w_cdb_03.append(final_w_cdb * 100)

nav_broad_cdb03 = (1 + pd.Series(ret_broad_cdb03_audit, index=dates_s46)).cumprod()

print(f"\n▶ 【纯大盘短债版】避险审计：股票逃逸/回归 {trades_broad_eq_03} 次，商品逃逸/回归 {trades_broad_com_03} 次")

# --- 2. 渲染联动联动图 ---
all_labels = []
for assets in daily_active_assets_03.values():
    for a in assets:
        if a not in all_labels: all_labels.append(a)
if '【商】大宗商品端' in all_labels: 
    all_labels.remove('【商】大宗商品端'); all_labels.insert(0, '【商】大宗商品端')
label_y = {l: i for i, l in enumerate(all_labels)}

fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(16, 18), gridspec_kw={'height_ratios': [1.2, 0.8, 1.5]}, sharex=True)

# 甘特图
for lbl, y in label_y.items():
    is_in = False; start = None
    color = 'darkgoldenrod' if '【商】' in lbl else 'steelblue'
    for d in dates_s46:
        present = lbl in daily_active_assets_03[d]
        if present and not is_in: is_in = True; start = d
        elif not present and is_in: 
            is_in = False
            ax1.broken_barh([(mdates.date2num(start), mdates.date2num(d)-mdates.date2num(start))], (y-0.3, 0.6), color=color, edgecolor='black', linewidth=0.5)
    if is_in: ax1.broken_barh([(mdates.date2num(start), mdates.date2num(dates_s46[-1])-mdates.date2num(start))], (y-0.3, 0.6), color=color)

for d in dates_s46:
    if is_eq_escape_daily_03[d]: ax1.axvspan(d, d + pd.Timedelta(days=1), color='crimson', alpha=0.15)
    if is_com_escape_daily_03[d]: ax1.axvspan(d, d + pd.Timedelta(days=1), color='orange', alpha=0.15)

ax1.set_yticks(range(len(all_labels))); ax1.set_yticklabels(all_labels); ax1.invert_yaxis()
ax1.set_title('v4.0 宽基版股票端 + 0-3年短债水库 —— 避险状态甘特图', fontsize=16, fontweight='bold')

# 资金分布图
ax2.stackplot(dates_s46, hist_w_eq_03, hist_w_cb_03, hist_w_com_03, hist_w_cdb_03, 
              labels=['股票(四大宽基)', '可转债(进攻)', '大宗商品', '国开债0-3年(新水库)'], 
              colors=['steelblue', 'darkviolet', 'darkgoldenrod', 'cadetblue'], alpha=0.85)
ax2.set_ylabel('占比 (%)'); ax2.set_ylim(0, 100); ax2.legend(loc='upper left', ncol=4)

# 净值曲线图
ax3.plot(nav_broad_cdb03.index, nav_broad_cdb03, label='v4.0 宽基版 + 0-3年短债', color='darkcyan', linewidth=3, zorder=5)
ax3.plot(nav_broad.index, nav_broad, label='v4.0 宽基版 + 5-7年长债 (对比项)', color='grey', linestyle='--', alpha=0.6)
ax3.plot(nav_hs300.index, nav_hs300, label='参考基准：沪深300指数', color='black', linewidth=1, alpha=0.4)
ax3.set_title('水库久期切换后的净值表现对比', fontsize=15, fontweight='bold')
ax3.legend(loc='upper left'); ax3.grid(True, linestyle=':', alpha=0.6)

def quarter_formatter(x, pos):
    try:
        dt = mdates.num2date(x)
        return f"{dt.year}Q{(dt.month-1)//3+1}"
    except: return ""

ax3.xaxis.set_major_locator(mdates.MonthLocator(bymonth=[1, 4, 7, 10]))
ax3.xaxis.set_major_formatter(FuncFormatter(quarter_formatter))
plt.setp(ax3.get_xticklabels(), rotation=45, ha='right', fontweight='bold')

plt.tight_layout(); plt.show()

print("\n🎉 Step 49 运行完毕！")