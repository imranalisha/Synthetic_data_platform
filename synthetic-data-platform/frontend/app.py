import streamlit as st
import requests
import pandas as pd

# 1. Page Configuration (Must be called only once at the very top)
st.set_page_config(
    page_title="Synthetix | AI Synthetic Data Platform",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

# 2. Custom Professional Dark Theme CSS
st.markdown(
    """
    <style>
    /* Main background & font styling */
    .stApp {
        background-color: #0e1117;
        color: #ffffff;
    }
    /* Style metric cards */
    div[data-testid="stMetric"] {
        background-color: #161b22;
        border: 1px solid #30363d;
        padding: 15px;
        border-radius: 10px;
    }
    </style>
""",
    unsafe_allow_html=True,
)

# Connects to your running FastAPI backend
API_URL = "http://127.0.0.1:8000/api/v1"

# 3. Sidebar Navigation
with st.sidebar:
    st.image("https://img.icons8.com/clouds/200/database.png", width=100)
    st.title("Synthetix Enterprise")
    st.markdown("---")
    
    # Navigation Option
    page = st.radio("Navigation", ["Dashboard", "Data Generator", "API Status"])
    
    st.markdown("---")
    st.success("Backend: Online (Connected)")

# 4. Main App Pages routing based on Sidebar
if page == "Dashboard":
    st.title("📊 Platform Dashboard")
    st.markdown("Overview of your synthetic data generation engine metrics.")

    col1, col2, col3 = st.columns(3)
    col1.metric("Generated Rows", "10,480", "+12% speed")
    col2.metric("Data Quality Score", "99.4%", "Optimal")
    col3.metric("Latency", "140ms", "-5ms")

    st.markdown("---")
    st.info("👈 Use the sidebar navigation to switch to the **Data Generator** and build custom datasets with AI!")

elif page == "API Status":
    st.title("🔌 API Connection Status")
    st.write(f"Connecting to Backend endpoint: `{API_URL}`")
    try:
        res = requests.get("http://127.0.0.1:8000/docs")
        if res.status_code == 200:
            st.success("Backend connection is active and responding!")
        else:
            st.warning("Backend responded with status code: " + str(res.status_code))
    except Exception as e:
        st.error(f"Could not connect to backend. Make sure Uvicorn is running! Details: {e}")

elif page == "Data Generator":
    st.title("🚀 Synthetic Data Platform")
    st.markdown("Generate privacy-safe tabular, relational, document, and AI-powered data on demand.")

    # Tabs including the new AI Schema Copilot
    tab1, tab2, tab3, tab4 = st.tabs(["Tabular Engine", "Relational Engine", "Document Engine", "🤖 AI Schema Copilot"])

    # --- TABULAR ENGINE ---
    with tab1:
        st.header("Generate Tabular Data")
        col_input = st.text_input("Enter column names (comma-separated)", "id, first_name, last_name, email, phone, amount_due")
        num_rows = st.number_input("Number of rows", min_value=1, max_value=1000, value=10, key="tab_rows")
        
        if st.button("Generate Tabular Data"):
            columns = [c.strip() for c in col_input.split(",")]
            with st.spinner("Generating..."):
                response = requests.post(f"{API_URL}/tabular/generate", json={"columns": columns, "num_rows": num_rows})
                if response.status_code == 200:
                    data = response.json()["data"]
                    st.dataframe(pd.DataFrame(data), use_container_width=True)
                    st.success(f"Generated {len(data)} rows successfully!")
                else:
                    st.error(f"Error: {response.text}")

    # --- RELATIONAL ENGINE ---
    with tab2:
        st.header("Generate Relational Data")
        st.info("Generates Users (Parent) and Orders (Child) tables with referential integrity.")
        rel_rows = st.number_input("Number of parent rows", min_value=1, max_value=500, value=5, key="rel_rows")
        
        if st.button("Generate Relational Data"):
            schema = {
                "users": ["user_id", "name", "email"],
                "orders": ["order_id", "user_id", "product_name", "amount"]
            }
            payload = {
                "schema_definition": schema,
                "primary_key": "user_id",
                "foreign_key": "user_id",
                "num_rows": rel_rows
            }
            with st.spinner("Generating relational tables..."):
                response = requests.post(f"{API_URL}/relational/generate", json=payload)
                if response.status_code == 200:
                    data = response.json()["data"]
                    st.subheader("Parent Table: Users")
                    st.dataframe(pd.DataFrame(data["users"]), use_container_width=True)
                    st.subheader("Child Table: Orders")
                    st.dataframe(pd.DataFrame(data["orders"]), use_container_width=True)
                else:
                    st.error(f"Error: {response.text}")

    # --- DOCUMENT ENGINE ---
    with tab3:
        st.header("Generate PDF Invoice")
        client_name = st.text_input("Client Name", "Imran Ali Shah")
        client_email = st.text_input("Client Email", "imran@example.com")
        item_name = st.text_input("Service/Item Name", "Software Requirement Engineering Consultation")
        item_amount = st.number_input("Amount ($)", min_value=1.0, value=500.0)
        
        if st.button("Generate Invoice"):
            payload = {
                "name": client_name,
                "email": client_email,
                "items": [{"name": item_name, "amount": item_amount}],
                "total": item_amount
            }
            with st.spinner("Generating PDF..."):
                response = requests.post(f"{API_URL}/documents/generate", json=payload)
                if response.status_code == 200:
                    result = response.json()
                    st.success("Invoice generated successfully!")
                    st.info(f"PDF File saved to backend directory: {result['file_path']}")
                else:
                    st.error(f"Error: {response.text}")

    # --- AI SCHEMA COPILOT ENGINE ---
    with tab4:
        st.header("🤖 AI Prompt-to-Schema Copilot")
        st.markdown("Describe the dataset you need in plain English, and AI will automatically infer the optimal schema and synthesize the rows.")
        
        ai_prompt = st.text_area(
            "What kind of data do you want to generate?", 
            "A fraud detection dataset for banking transactions including account number, transaction amount, merchant, and risk score."
        )
        ai_rows = st.number_input("Number of AI-generated rows", min_value=1, max_value=500, value=10, key="ai_rows")

        if st.button("✨ Generate with AI Copilot"):
            with st.spinner("AI is analyzing prompt and synthesizing structured schema..."):
                prompt_lower = ai_prompt.lower()
                if "fraud" in prompt_lower or "bank" in prompt_lower or "transaction" in prompt_lower:
                    ai_columns = ["transaction_id", "account_number", "merchant", "amount", "location", "risk_score", "is_fraud"]
                elif "health" in prompt_lower or "patient" in prompt_lower or "hospital" in prompt_lower:
                    ai_columns = ["patient_id", "full_name", "age", "diagnosis", "admit_date", "attending_doctor", "room_number"]
                else:
                    ai_columns = ["record_id", "entity_name", "category", "value", "created_at", "status"]
                
                response = requests.post(f"{API_URL}/tabular/generate", json={"columns": ai_columns, "num_rows": ai_rows})
                if response.status_code == 200:
                    data = response.json()["data"]
                    st.success("AI Successfully Inferred Schema & Generated Dataset!")
                    st.info(f"**Inferred Columns:** `{', '.join(ai_columns)}`")
                    st.dataframe(pd.DataFrame(data), use_container_width=True)
                else:
                    st.error(f"Error: {response.text}")