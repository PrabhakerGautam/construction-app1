import streamlit as st
import pandas as pd
import os
from datetime import date

# --- CONFIGURATION ---
st.set_page_config(page_title="Construction Pro", page_icon="🏗️", layout="wide")

# File Names
LABOR_FILE = 'labor.csv'
EXPENSE_FILE = 'expenses.csv'
PROGRESS_FILE = 'site_diary.csv'

# --- HELPER FUNCTIONS ---
def save_data(df, filename):
    """Saves the dataframe to a CSV file"""
    df.to_csv(filename, index=False)

def load_data(filename, columns):
    """Loads CSV and fixes NaN/Empty number errors"""
    if not os.path.exists(filename):
        df = pd.DataFrame(columns=columns)
        df.to_csv(filename, index=False)
        return df
    
    # Load and Fix Numbers
    df = pd.read_csv(filename)
    numeric_cols = ["Wage", "Attendance", "Paid_Today", "Cost", "Earned"]
    for col in numeric_cols:
        if col in df.columns:
            # Force empty cells to be 0
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
    return df

# --- LOAD DATA ---
df_labor = load_data(LABOR_FILE, ["Date", "Worker", "Role", "Wage", "Attendance", "Paid_Today", "Notes"])
df_exp = load_data(EXPENSE_FILE, ["Date", "Item", "Category", "Cost", "Paid_To"])
df_prog = load_data(PROGRESS_FILE, ["Date", "Work_Description"])

# --- SIDEBAR ---
st.sidebar.title("🏗️ Site Manager")
menu = st.sidebar.radio("Navigate", ["Dashboard 📊", "Bulk Attendance 🚀", "Single Entry 👷", "Material/Bills 🧱", "Reports 📥"])

# --- 1. DASHBOARD ---
if menu == "Dashboard 📊":
    st.title("📊 Project Insights")
    
    # Calculations
    df_labor["Earned"] = df_labor["Wage"] * df_labor["Attendance"]
    total_labor_paid = df_labor["Paid_Today"].sum()
    total_labor_earned = df_labor["Earned"].sum()
    labor_due = total_labor_earned - total_labor_paid
    
    total_material = df_exp["Cost"].sum()
    grand_total = total_material + total_labor_paid
    
    # Metrics
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("💰 Total Spent", f"₹{grand_total:,.0f}")
    c2.metric("🧱 Material Cost", f"₹{total_material:,.0f}")
    c3.metric("👷 Labor Paid", f"₹{total_labor_paid:,.0f}")
    c4.metric("⚠️ Pending Dues", f"₹{labor_due:,.0f}", delta_color="inverse")
    
    st.markdown("---")
    
    # Charts
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Where is the money going?")
        spending_data = df_exp.groupby("Category")["Cost"].sum().reset_index()
        spending_data.loc[len(spending_data)] = ['Labor Payments', total_labor_paid]
        st.bar_chart(spending_data, x="Category", y="Cost", color="#FF4B4B")
        
    with col2:
        st.subheader("Pending Dues List")
        if not df_labor.empty:
            worker_summary = df_labor.groupby("Worker")[["Earned", "Paid_Today"]].sum()
            worker_summary["Balance_Due"] = worker_summary["Earned"] - worker_summary["Paid_Today"]
            pending = worker_summary[worker_summary["Balance_Due"] > 10] # Show only if > 10rs due
            st.dataframe(pending[["Balance_Due"]].sort_values("Balance_Due", ascending=False))

# --- 2. BULK ATTENDANCE ---
elif menu == "Bulk Attendance 🚀":
    st.title("⚡ Fast Attendance")
    
    workers = df_labor["Worker"].unique().tolist()
    if not workers:
        st.warning("No workers found. Go to 'Single Entry' to add your first worker.")
    
    with st.form("bulk_form"):
        date_in = st.date_input("Date", date.today())
        selected = st.multiselect("Select Present Workers", workers)
        
        c1, c2 = st.columns(2)
        wage = c1.number_input("Standard Wage (₹)", value=600.0)
        att = c2.selectbox("Attendance", [1.0, 0.5], format_func=lambda x: "Full Day" if x==1 else "Half Day")
        
        if st.form_submit_button("Mark Present"):
            new_rows = []
            for w in selected:
                new_rows.append({
                    "Date": date_in, "Worker": w, "Role": "Regular", 
                    "Wage": wage, "Attendance": att, "Paid_Today": 0.0, "Notes": "Bulk"
                })
            df_labor = pd.concat([df_labor, pd.DataFrame(new_rows)], ignore_index=True)
            save_data(df_labor, LABOR_FILE)
            st.success(f"Marked {len(selected)} workers!")

# --- 3. SINGLE ENTRY ---
elif menu == "Single Entry 👷":
    st.title("👷 Individual Entry")
    
    # Worker Selector
    existing = df_labor["Worker"].unique().tolist()
    mode = st.radio("Mode", ["Existing Worker", "New Worker"], horizontal=True)
    
    final_name = ""
    if mode == "Existing Worker":
        final_name = st.selectbox("Select Name", existing) if existing else ""
    else:
        final_name = st.text_input("Enter New Name")
        
    with st.form("single_form", clear_on_submit=True):
        st.write(f"Entry for: **{final_name}**")
        d_date = st.date_input("Date", date.today())
        
        c1, c2 = st.columns(2)
        wage = c1.number_input("Wage (₹)", value=600.0)
        att = c2.selectbox("Attendance", [1.0, 0.5, 0.0], format_func=lambda x: "Full Day" if x==1 else ("Half Day" if x==0.5 else "Absent"))
        
        paid = st.number_input("Cash Given (Kharcha)", value=0.0)
        
        if st.form_submit_button("Save Entry"):
            if not final_name:
                st.error("Name is required!")
            else:
                new_row = pd.DataFrame([{
                    "Date": d_date, "Worker": final_name, "Role": "Labor",
                    "Wage": wage, "Attendance": att, "Paid_Today": paid, "Notes": "Single"
                }])
                df_labor = pd.concat([df_labor, new_row], ignore_index=True)
                save_data(df_labor, LABOR_FILE)
                st.success("Saved!")

# --- 4. EXPENSES ---
elif menu == "Material/Bills 🧱":
    st.title("🧱 Expenses")
    
    with st.form("exp_form", clear_on_submit=True):
        d_date = st.date_input("Date", date.today())
        item = st.text_input("Item (e.g. Cement)")
        
        c1, c2 = st.columns(2)
        cost = c1.number_input("Cost (₹)", value=0.0)
        cat = c2.selectbox("Category", ["Material", "Transport", "Food", "Other"])
        
        if st.form_submit_button("Save Expense"):
            new_row = pd.DataFrame([{
                "Date": d_date, "Item": item, "Category": cat, "Cost": cost, "Paid_To": ""
            }])
            df_exp = pd.concat([df_exp, new_row], ignore_index=True)
            save_data(df_exp, EXPENSE_FILE)
            st.success("Expense Saved!")
            
    st.dataframe(df_exp.tail(5))

# --- 5. REPORTS ---
elif menu == "Reports 📥":
    st.title("📂 Download Data")
    tab1, tab2 = st.tabs(["Labor", "Expenses"])
    
    with tab1:
        st.dataframe(df_labor)
        st.download_button("Download Labor CSV", df_labor.to_csv(index=False), "labor.csv")
        
    with tab2:
        st.dataframe(df_exp)
        st.download_button("Download Expense CSV", df_exp.to_csv(index=False), "expenses.csv")