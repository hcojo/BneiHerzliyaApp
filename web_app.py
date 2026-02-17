import streamlit as st
import pandas as pd
import requests
import io
import re

# 1. Page Configuration & RTL (Right-to-Left) Fix for Hebrew
st.set_page_config(page_title="לוח אירועים בני הרצליה", layout="centered")
st.markdown("""
    <style>
        /* 1. Global RTL Direction */
        .stApp { 
            direction: rtl; 
        }
        
        /* 2. Force Right Alignment for all Text, Headers, and Markdown */
        [data-testid="stMarkdownContainer"], 
        [data-testid="stMarkdownContainer"] * {
            text-align: right !important;
            direction: rtl !important;
        }
        
        /* 3. Dropdown Menu Fixes */
        .stSelectbox label { 
            text-align: right !important; 
            width: 100%; 
        }
        [data-baseweb="select"] {
            direction: rtl;
        }
        
        /* 4. Success/Error Messages (Alerts) */
        [data-testid="stAlert"] * {
            text-align: right !important;
            direction: rtl !important;
        }
        
        /* 5. Mobile Adjustments */
        @media (max-width: 768px) {
            html, body, [class*="css"] {
                font-size: 14px !important;
            }
            .block-container {
                padding: 1.5rem 1rem !important;
            }
        }
    </style>
""", unsafe_allow_html=True)

st.title("🏊 לוח אירועים - בני הרצליה")
st.write("בחר קבוצה כדי לראות את כל האירועים הרלוונטיים עבורה.")

# 2. Download and Cache Data (Downloads once every 5 minutes to keep it fast)
@st.cache_data(ttl=300)
def load_data():
    sheet_id = "1YlWC_x_ZZtR22p-R1bI_Nvl015bbE7ge"
    url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=xlsx&gid=1957947665"
    
    response = requests.get(url)
    response.raise_for_status()
    raw_df = pd.read_excel(io.BytesIO(response.content), header=None)

    # Find headers
    header_idx = -1
    for idx, row in raw_df.iterrows():
        if any("קבוצות משתתפות" in str(cell) for cell in row.values):
            header_idx = idx
            break

    if header_idx == -1:
        st.error("שגיאה: לא נמצאה עמודת 'קבוצות משתתפות'.")
        return None, None

    # Set headers and cleanup
    raw_df.columns = [str(c).strip() for c in raw_df.iloc[header_idx]]
    df = raw_df.iloc[header_idx + 1:].reset_index(drop=True)
    
    # Identify specific columns
    col_mapping = {
        'target': next((c for c in df.columns if "קבוצות משתתפות" in c), None),
        'week': next((c for c in df.columns if "שבוע" in c or "תאריך" in c), None),
        'event': next((c for c in df.columns if "אירוע" in c), None),
        'loc': next((c for c in df.columns if "אולם" in c or "מיקום" in c), None)
    }

    # Forward fill dates
    if col_mapping['week']:
        df[col_mapping['week']] = df[col_mapping['week']].ffill()

    return df, col_mapping

# 3. Main App Logic
df, col_mapping = load_data()

if df is not None and col_mapping['target']:
    # Extract unique groups
    unique_groups = set()
    for val in df[col_mapping['target']].dropna():
        parts = re.split(r'[,\n/]', str(val))
        for part in parts:
            clean_part = part.strip()
            if clean_part and clean_part.lower() != 'nan':
                unique_groups.add(clean_part)

    clean_groups = sorted(list(unique_groups))

    # Dropdown Menu
    selected_group = st.selectbox("חיפוש קבוצה:", [""] + clean_groups)

    if selected_group:
        # Filter the data
        mask = df[col_mapping['target']].astype(str).str.contains(selected_group, regex=False, na=False)
        filtered_df = df[mask].copy()

        # Keep only the relevant columns in the exact order needed for Streamlit's visual layout
        display_cols = []
        rename_dict = {}
        
        # 1. Left-most column
        display_cols.append(col_mapping['target'])
        rename_dict[col_mapping['target']] = "קבוצות משתתפות"

        # 2. Middle-left column
        if col_mapping['loc']: 
            display_cols.append(col_mapping['loc'])
            rename_dict[col_mapping['loc']] = "מיקום"
            
        # 3. Middle-right column
        if col_mapping['week']: 
            display_cols.append(col_mapping['week'])
            rename_dict[col_mapping['week']] = "שבוע/תאריך"
            
        # 4. Right-most column
        if col_mapping['event']: 
            display_cols.append(col_mapping['event'])
            rename_dict[col_mapping['event']] = "אירוע"

        final_df = filtered_df[display_cols].rename(columns=rename_dict)
        
        # Clean up 'nan' text in the table
        final_df = final_df.fillna("").astype(str).replace('nan', '')

        st.success(f"נמצאו {len(final_df)} אירועים עבור: {selected_group}")
        
        # Display the table
        #st.dataframe(final_df, hide_index=True, use_container_width=True)
        st.write("---") # Visual separator
        for index, row in final_df.iterrows():
            with st.container():
                # Make the Event name stand out
                st.markdown(f"**{row.get('אירוע', 'ללא שם אירוע')}**")
                
                # Display the details below it
                col1, col2 = st.columns(2)
                with col1:
                    st.write(f"**מיקום:** {row.get('מיקום', '')}")
                with col2:
                    st.write(f"**תאריך:** {row.get('שבוע/תאריך', '')}")
                
                st.write(f"**קבוצות:** {row.get('קבוצות משתתפות', '')}")
                st.markdown("<hr style='margin-top: 5px; margin-bottom: 15px; border: 0; border-top: 1px solid #e6e6e6;'>", unsafe_allow_html=True)
                #st.write("---") # Separator between events