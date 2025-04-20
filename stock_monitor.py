import time
import requests
from plyer import notification
import logging
from datetime import datetime
import json
import os


# 配置日志
os.chdir(os.path.dirname(__file__))
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('stock_monitor.log'),
        logging.StreamHandler()
    ]
)

def fetch_rankings():
    """获取东方财富网股吧排名数据"""
    url = "https://emappdata.eastmoney.com/stockrank/getAllCurrentList"
    params = {
        "appId": "appId01",
        "pageNo": 1,
        "pageSize": "100"
    }
    
    try:
        response = requests.post(url, json=params)
        response.raise_for_status()
        data = response.json()
        
        rankings = {}
        for item in data.get("data", []):
            code = item["sc"]  # 股票代码
            rank = item["rk"]  # 排名
            name = item.get("n", "")  # 股票名称
            
            # 如果名称为空，尝试从另一个API获取
            if not name:
                name = get_stock_name_from_api(code)
            
            rankings[code] = {
                'name': name,
                'rank': rank
            }
        
        return rankings
        
    except Exception as e:
        logging.error(f"获取数据失败: {str(e)}")
        return {}

def get_stock_name_from_api(stock_code):
    """从另一个API获取股票名称"""
    url = f"http://push2.eastmoney.com/api/qt/stock/get"
    params = {
        "secid": f"{'0' if stock_code.startswith('SZ') else '1'}.{stock_code[2:]}",
        "fields": "f58"  # 只获取股票名称字段
    }
    
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()
        if data.get("data"):
            return data["data"].get("f58", "未知")
    except Exception as e:
        logging.error(f"获取股票名称失败: {str(e)}")
    return "未知"

def send_notification(title, message):
    """发送系统通知"""
    try:
        notification.notify(
            title=title,
            message=message,
            app_name="股票监控系统",
            timeout=10
        )
    except Exception as e:
        logging.error(f"发送通知失败: {str(e)}")

def monitor():
    """监控股票排名变化"""
    last_rankings = {}
    logging.info("开始监控股票排名...")
    
    while True:
        try:
            current_rankings = fetch_rankings()
            if not current_rankings:
                logging.warning("无法获取数据，稍后重试...")
                time.sleep(60)
                continue
            
            if last_rankings:
                # 检测新股票
                new_stocks = set(current_rankings.keys()) - set(last_rankings.keys())
                for code in new_stocks:
                    stock = current_rankings[code]
                    msg = f"新股票进入前100！代码：{code}，名称：{stock['name']}，排名：{stock['rank']}"
                    logging.info(msg)
                    send_notification("新股票警报", msg)
                
                # 检测排名跃升
                for code in current_rankings:
                    if code in last_rankings:
                        last_rank = last_rankings[code]['rank']
                        current_rank = current_rankings[code]['rank']
                        if (last_rank - current_rank) >= 10:
                            msg = f"{current_rankings[code]['name']} ({code}) 排名上升 {last_rank - current_rank} 名，从 {last_rank} 升至 {current_rank}"
                            logging.info(msg)
                            send_notification("排名跃升警报", msg)
            
            last_rankings = current_rankings.copy()
            time.sleep(60)  # 每分钟检查一次
            
        except Exception as e:
            logging.error(f"监控过程中发生错误: {str(e)}")
            time.sleep(60)

if __name__ == "__main__":
    try:
        monitor()
    except KeyboardInterrupt:
        logging.info("程序已停止") 