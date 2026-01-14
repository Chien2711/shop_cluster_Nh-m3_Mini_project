import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import sys
import os

# Thêm đường dẫn src để import library của Cô
sys.path.append(os.path.abspath('src'))
from cluster_library import DataCleaner, RuleBasedCustomerClusterer

# Cấu hình trang
st.set_page_config(page_title="Customer Clustering Dashboard", layout="wide")
st.title("🛍️ Phân cụm Khách hàng (Rule-Based + RFM)")
st.markdown("---")

# --- 1. SIDEBAR: CẤU HÌNH ---
st.sidebar.header("🛠️ Tham số Mô hình")

# Tham số luật
top_k = st.sidebar.slider("Số lượng luật (Top-K):", 10, 200, 50)

# Tham số đặc trưng (Đúng yêu cầu Advanced của Cô)
st.sidebar.subheader("Cấu hình Đặc trưng")
weight_option = st.sidebar.selectbox("Trọng số luật (Weighting):", ["none", "lift", "confidence", "lift_x_conf"])
use_rfm = st.sidebar.checkbox("Kết hợp RFM?", value=True, help="Ghép thêm Recency, Frequency, Monetary")

# Tham số phân cụm
st.sidebar.subheader("Phân cụm KMeans")
k_clusters = st.sidebar.slider("Số cụm (K):", 2, 10, 3)
btn_run = st.sidebar.button("🚀 CHẠY PHÂN TÍCH", type="primary")

# --- 2. HÀM XỬ LÝ ---
@st.cache_data
def load_and_process(k, weight, rfm_flag):
    # --- CẤU HÌNH ĐƯỜNG DẪN MẶC ĐỊNH (CỦA CÔ) ---
    # Bạn đảm bảo tên file trong thư mục đúng y hệt thế này nhé
    rules_path = os.path.join('data', 'processed', 'rules_apriori_filtered.csv')
    raw_path = os.path.join('data', 'raw', 'online_retail.csv') 

    # Kiểm tra file tồn tại
    if not os.path.exists(rules_path):
        return None, None, f"❌ Không tìm thấy file luật: {rules_path}. Bạn hãy kiểm tra lại thư mục data/processed."
    if not os.path.exists(raw_path):
        return None, None, f"❌ Không tìm thấy file gốc: {raw_path}. Bạn hãy kiểm tra lại thư mục data/raw."

    # Init Cleaner & Load Data
    # Lưu ý: Ta chỉ load 1 phần dữ liệu để demo cho nhanh (head(10000))
    # Nếu máy mạnh, bạn có thể bỏ .head(10000) đi để chạy full
    try:
        if raw_path.endswith('.xlsx'):
            df = pd.read_excel(raw_path).head(10000) 
        else:
            df = pd.read_csv(raw_path, encoding="ISO-8859-1").head(10000)
            
        # Chuẩn hóa tên cột (đề phòng file raw của cô tên cột khác)
        df.rename(columns={
            'Customer ID': 'CustomerID', 
            'Price': 'UnitPrice', 
            'Invoice': 'InvoiceNo'
        }, inplace=True)
        
    except Exception as e:
        return None, None, f"Lỗi đọc file raw: {e}"

    # Init Clusterer
    clusterer = RuleBasedCustomerClusterer(df_clean=df)
    
    # Load Rules
    try:
        clusterer.load_rules(rules_path, top_k=k)
    except Exception as e:
        return None, None, f"Lỗi đọc file rules (kiểm tra xem file csv có cột antecedents_str chưa?): {e}"
    
    # Tạo đặc trưng (Hàm xịn của cô)
    try:
        X, meta_df = clusterer.build_final_features(
            weighting=weight,
            use_rfm=rfm_flag,
            rfm_scale=True
        )
    except Exception as e:
        return None, None, f"Lỗi tạo đặc trưng: {e}"
    
    return clusterer, X, meta_df

# --- 3. MAIN APP ---
if btn_run:
    with st.spinner("Đang xử lý dữ liệu của Cô..."):
        try:
            clusterer, X, meta_df = load_and_process(top_k, weight_option, use_rfm)
            
            if isinstance(meta_df, str): # Nếu hàm trả về chuỗi lỗi
                st.error(meta_df)
            else:
                # Fit KMeans
                labels = clusterer.fit_kmeans(X, n_clusters=k_clusters)
                meta_df['Cluster'] = labels
                
                st.success(f"✅ Đã phân thành {k_clusters} cụm thành công!")
                
                # --- VẼ BIỂU ĐỒ ---
                col1, col2 = st.columns([2, 1])
                
                with col1:
                    st.subheader("Biểu đồ PCA (2D)")
                    # Giảm chiều dữ liệu để vẽ
                    X_2d = clusterer.project_2d(X)
                    
                    fig, ax = plt.subplots(figsize=(8, 5))
                    scatter = ax.scatter(X_2d[:,0], X_2d[:,1], c=labels, cmap='viridis', alpha=0.6)
                    plt.colorbar(scatter, label='Cluster')
                    ax.set_xlabel("PCA Component 1")
                    ax.set_ylabel("PCA Component 2")
                    st.pyplot(fig)
                
                with col2:
                    st.subheader("Thống kê Cụm")
                    counts = meta_df['Cluster'].value_counts().reset_index()
                    counts.columns = ['Cụm', 'Số khách']
                    st.dataframe(counts, hide_index=True)
                    
                    if use_rfm:
                        st.caption("Trung bình RFM:")
                        rfm_stats = meta_df.groupby('Cluster')[['Recency', 'Frequency', 'Monetary']].mean()
                        st.dataframe(rfm_stats.style.format("{:.1f}"))

        except Exception as e:
            st.error(f"Lỗi không mong muốn: {e}")