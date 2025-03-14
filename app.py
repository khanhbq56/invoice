# app.py
import os
import base64
import streamlit as st
from google import genai
import tempfile
from PIL import Image
import io
import pandas as pd
import json
import re

# --- Module Setup ---
def setup_page():
    """Configure the page settings and theme"""
    st.set_page_config(
        page_title="Japanese Invoice Extractor",
        page_icon="📃",
        layout="wide",
    )
    
    # Custom CSS for blue theme
    st.markdown("""
    <style>
    .main {
        background-color: #f0f5ff;
    }
    .stButton>button {
        background-color: #1e88e5;
        color: white;
    }
    .stTextInput>div>div>input {
        border-color: #1e88e5;
    }
    h1, h2, h3 {
        color: #0d47a1;
    }
    .stProgress > div > div > div {
        background-color: #1e88e5;
    }
    .css-1offfwp {
        color: #0d47a1 !important;
    }
    .css-10trblm {
        color: #0d47a1 !important;
    }
    </style>
    """, unsafe_allow_html=True)

# --- API Module ---
def extract_data_from_invoice(image_files):
    """Extract structured data from invoice images using Gemini API"""
    # Initialize the client with hardcoded API key
    client = genai.Client(api_key='AIzaSyDVQIpFL4KqEEDTDQkUwMYM2149huI9rLY')
    
    # Select the model
    model = "gemini-2.0-pro-exp-02-05"
    
    # Prepare the prompt
    prompt = """この仕入伝票画像からすべてのデータを抽出し、以下の構造で整理してください：

【基本情報】
- 伝票番号/管理番号
- 日付情報
- 店舗/取引先情報

【商品情報】
以下の表形式で商品リストを抽出：
| No. | 商品名 | 商品コード | 数量 | 単価 | 金額 | 備考 |

【金額情報】
- 合計金額
- 税金情報

【その他情報】
- 備考/特記事項
- 担当者情報

レイアウトが異なる場合でも、上記カテゴリに情報を分類して抽出してください。
もし複数の画像が入力された場合も、各画像について上記のフォーマットに従い、個別に抽出し、画像ごとに区切って整理してください。
余分な挨拶や確認のメッセージは不要です。直接指定されたフォーマットでデータ整理の結果のみを出力してください。
"""
    
    # Create content parts for the request
    parts = []
    
    # Add all images to the parts
    for image_file in image_files:
        # Read the image file
        image_bytes = image_file.getvalue()
        
        # Determine MIME type
        file_name = image_file.name.lower()
        mime_type = "image/jpeg"  # Default
        if file_name.endswith(".png"):
            mime_type = "image/png"
        
        # Add the image as a part
        parts.append({"inline_data": {"mime_type": mime_type, "data": base64.b64encode(image_bytes).decode()}})
    
    # Add the prompt as a part
    parts.append({"text": prompt})
    
    # Create the request
    request = {
        "contents": [
            {
                "role": "user",
                "parts": parts
            }
        ]
    }
    
    try:
        # Make the API call
        response = client.models.generate_content(model=model, **request)
        return response.text
    except Exception as e:
        st.error(f"API Error: {str(e)}")
        return None

# --- UI Module ---
def render_sidebar():
    """Render the sidebar with information only (no API key input)"""
    with st.sidebar:
        st.markdown("### 📑 アプリについて")
        st.info(
            "伝票画像をアップロードすると、基本情報、商品詳細、"
            "合計金額などが抽出されます。"
        )

def render_main_area():
    """Render the main area of the application"""
    st.title("📃 日本語伝票データ抽出ツール")
    st.markdown("日本語の伝票・発注書から情報を自動抽出するツールです。画像をアップロードして、データを抽出してください。")
    
    # File uploader
    uploaded_files = st.file_uploader(
        "伝票画像をアップロード",
        accept_multiple_files=True,
        type=["png", "jpg", "jpeg"],
        help="複数の画像をアップロードできます"
    )
    
    if uploaded_files:
        st.write(f"{len(uploaded_files)}つのファイルがアップロードされました")
        
        # Display image previews
        cols = st.columns(min(3, len(uploaded_files)))
        for i, image_file in enumerate(uploaded_files):
            col_idx = i % len(cols)
            with cols[col_idx]:
                st.image(Image.open(image_file), caption=f"画像 {i+1}", use_container_width=True)
                image_file.seek(0)  # Reset file pointer after reading
        
        # Extract button
        if st.button("🔍 データ抽出開始", use_container_width=True):
            with st.spinner("伝票からデータを抽出中..."):
                result = extract_data_from_invoice(uploaded_files)
                if result:
                    st.session_state["extraction_result"] = result
                    st.session_state["edited_result"] = result  # Initialize edited result
                    st.success("データの抽出が完了しました！")
    
    # Display results if available
    if "extraction_result" in st.session_state:
        display_results()

def display_results():
    """Display the extracted results with improved editing synchronization"""
    st.markdown("## 📊 抽出結果")
    
    # Create tabs for viewing and editing
    tab1, tab2 = st.tabs(["抽出結果", "編集"])
    
    with tab1:
        # Display the most current version (either edited or original)
        current_result = st.session_state.get("edited_result", st.session_state["extraction_result"])
        st.markdown(current_result)
    
    with tab2:
        # Use the callback to update both states simultaneously
        def on_text_change():
            st.session_state["extraction_result"] = st.session_state["text_editor"]
            st.session_state["edited_result"] = st.session_state["text_editor"]
            
        edited_text = st.text_area(
            "結果を編集",
            value=st.session_state.get("edited_result", st.session_state["extraction_result"]),
            height=500,
            key="text_editor",
            on_change=on_text_change
        )
    
    # Download button
    col1, col2 = st.columns([1, 1])
    with col1:
        if st.button("📥 Markdownとしてダウンロード", use_container_width=True):
            content_to_download = st.session_state.get("edited_result", st.session_state["extraction_result"])
            st.download_button(
                label="ダウンロードを確認",
                data=content_to_download,
                file_name="extracted_invoice_data.md",
                mime="text/markdown"
            )
    
    with col2:
        if st.button("📥 CSVテーブルとしてダウンロード", use_container_width=True):
            content_to_download = st.session_state.get("edited_result", st.session_state["extraction_result"])
            # Try to extract tables from markdown
            tables_data = extract_tables_from_markdown(content_to_download)
            if tables_data:
                csv_data = convert_tables_to_csv(tables_data)
                st.download_button(
                    label="テーブルCSVをダウンロード",
                    data=csv_data,
                    file_name="invoice_tables.csv",
                    mime="text/csv"
                )
            else:
                st.error("テーブルデータを抽出できませんでした")

# --- Data Processing Module ---
def extract_tables_from_markdown(markdown_text):
    """Extract tables from markdown text"""
    # Find all markdown tables using regex
    table_pattern = r"\|(.+\|)+\n\|([\s-]+\|)+\n(\|(.+\|)+\n)+"
    tables = re.findall(table_pattern, markdown_text)
    
    if not tables:
        return []
    
    # Extract and parse each table
    all_tables = []
    for table_match in re.finditer(table_pattern, markdown_text):
        table_text = table_match.group(0)
        rows = table_text.strip().split('\n')
        
        # Remove the separator line (second line)
        if len(rows) > 1:
            header = rows[0].strip()
            data_rows = rows[2:]  # Skip header and separator
            
            # Parse header
            header_cols = [col.strip() for col in header.split('|')[1:-1]]
            
            # Parse data rows
            parsed_rows = []
            for row in data_rows:
                cols = [col.strip() for col in row.split('|')[1:-1]]
                parsed_rows.append(cols)
            
            all_tables.append({
                "header": header_cols,
                "rows": parsed_rows
            })
    
    return all_tables

def convert_tables_to_csv(tables):
    """Convert extracted tables to CSV format"""
    if not tables:
        return ""
    
    # Combine all tables into one CSV
    all_data = []
    
    for i, table in enumerate(tables):
        # Add table header
        if i > 0:
            all_data.append(["", ""])  # Empty row between tables
            all_data.append([f"Table {i+1}", ""])
        
        all_data.append(table["header"])
        all_data.extend(table["rows"])
    
    # Convert to CSV string
    csv_data = io.StringIO()
    for row in all_data:
        csv_data.write(",".join([f'"{cell}"' for cell in row]))
        csv_data.write("\n")
    
    return csv_data.getvalue()

# --- Main Application ---
def main():
    """Main application entry point"""
    # Setup page
    setup_page()
    
    # Render sidebar
    render_sidebar()
    
    # Render main area
    render_main_area()

if __name__ == "__main__":
    main()