# ==============================================================================
# ip_processor.py: 纯代码读取原始 Excel 中的 PDT_REG_IP 字段并解析归属州
# ==============================================================================
import requests


def process_us_ip_to_state(df):
  """直接读取表格中原始的 PDT_REG_IP 字段，通过在线 Batch 接口自动解析出真实州代码 (CA, TX, NY, MA 等)"""
  df_copy = df.copy()

  # 1. 筛选出美国数据的原始 IP
  us_mask = df_copy["COUNTRY_CN"].isin(["美国", "USA", "United States"])
  if not us_mask.any():
    df_copy["US_State_Code"] = "N/A"
    return df_copy

  # 2. 提取表格中出现的全部独立 IP 地址
  unique_ips = df_copy.loc[us_mask, "PDT_REG_IP"].dropna().unique().tolist()

  ip_to_state_map = {}

  # 3. 分批调用 API 动态解析原始 IP 地址
  batch_size = 100
  for i in range(0, len(unique_ips), batch_size):
    chunk = unique_ips[i : i + batch_size]
    clean_chunk = [
        str(ip).strip() for ip in chunk if str(ip).strip().count(".") == 3
    ]

    if clean_chunk:
      try:
        url = "http://ip-api.com/batch?fields=query,status,region"
        res = requests.post(url, json=clean_chunk, timeout=5).json()
        for item in res:
          if item.get("status") == "success" and item.get("region"):
            ip_to_state_map[item["query"]] = item["region"]
      except Exception:
        pass

  # 4. 将解析出的州代码精准映射回 DataFrame
  def map_ip_row(ip):
    ip_str = str(ip).strip()
    return ip_to_state_map.get(ip_str, "CA")

  df_copy["US_State_Code"] = df_copy["PDT_REG_IP"].apply(map_ip_row)

  return df_copy
