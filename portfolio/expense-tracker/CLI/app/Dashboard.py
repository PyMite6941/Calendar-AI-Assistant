import streamlit as st
import os
import sys
from datetime import datetime as _datetime
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from CLI.app.streamlit_setup import init_st, sync_data

_ocr_available = False
try:
    from backend.ocr import parse_receipt as _parse_receipt
    _ocr_available = True
except Exception:
    pass

init_st()

st.title('Web-based Expense and Income Tracking')

tab_dashboard, tab_add, tab_delete, tab_edit, tab_expenses, tab_income, tab_subscriptions = st.tabs([
    "Dashboard", "Add", "Delete", "Edit", "View Expenses", "View Income", "View Subscriptions"
])

with tab_dashboard:
    if st.session_state.expenses:
        filtered_expenses = [expense for expense in st.session_state.expenses if expense['date'][:7] == st.session_state.current_month]
        monthly_expenses = sum(expense['price'] for expense in filtered_expenses)
        st.metric('Monthly Expenses', f"{monthly_expenses:.2f} USD")
    else:
        st.write("No expenses found.")
    if st.session_state.income:
        filtered_income = [income for income in st.session_state.income if income['date'][:7] == st.session_state.current_month]
        monthly_income = sum(income['amount'] for income in filtered_income)
        st.metric('Monthly Income', f"{monthly_income:.2f} USD")
    else:
        st.write("No income found.")
    budget_totals = {}
    for expense in st.session_state.expenses:
        if expense['date'][:7] == st.session_state.current_month:
            tag = expense['tags']
            budget_totals[tag] = budget_totals.get(tag, 0) + expense['price']
    for budget in st.session_state.budget:
        total_spent = budget_totals.get(budget['category'], 0)
        limit = float(budget['amount'])
        if limit < total_spent:
            st.warning(f"{budget['category']} budget has been surpassed by {total_spent - limit:.2f}.")
        elif limit == total_spent:
            st.warning(f"{budget['category']} budget has reached its limit.")

with tab_add:
    choice = st.selectbox('What to add?', options=['Expenses', 'Income', 'Budget', 'Subscription', 'Goal'], key='add_choice')
    if choice == 'Expenses':
        with st.expander('Scan a Receipt', expanded=False):
            if not _ocr_available:
                st.info("Receipt OCR requires Google Cloud Vision. Set the GOOGLE_APPLICATION_CREDENTIALS environment variable to enable.")
            else:
                receipt_img = st.file_uploader("Upload receipt image", type=["png", "jpg", "jpeg", "webp"], key="receipt_uploader")
                if receipt_img and st.button("Scan Receipt", key="scan_receipt_btn"):
                    with st.spinner("Scanning receipt..."):
                        try:
                            result = _parse_receipt(receipt_img.read())
                            st.session_state['add_exp_purchased'] = result.get('merchant', '')
                            st.session_state['add_exp_amount'] = float(result.get('total', 0.0))
                            date_str = result.get('date', '')
                            if date_str:
                                for fmt in ('%Y-%m-%d', '%m/%d/%Y', '%m-%d-%Y', '%m/%d/%y', '%d/%m/%Y'):
                                    try:
                                        st.session_state['add_exp_date'] = _datetime.strptime(date_str, fmt).date()
                                        break
                                    except ValueError:
                                        continue
                            st.session_state['_ocr_last'] = result
                            st.rerun()
                        except Exception as e:
                            st.error(f"OCR failed: {e}")
                if '_ocr_last' in st.session_state:
                    r = st.session_state['_ocr_last']
                    st.caption(f"Last scan: **{r.get('merchant', '')}** — {float(r.get('total', 0)):.2f} {r.get('currency', 'USD')} on {r.get('date', '')}")
                    if st.button("Clear", key="clear_ocr_btn"):
                        for k in ['_ocr_last', 'add_exp_purchased', 'add_exp_amount', 'add_exp_date']:
                            st.session_state.pop(k, None)
                        st.rerun()
        with st.expander('Recurring Expenses', expanded=False):
            if not st.session_state.recurring_expenses:
                st.write("No recurring expenses found.")
            else:
                for i, expense in enumerate(st.session_state.recurring_expenses):
                    col1, col2, col3, col4 = st.columns([3, 2, 2, 2])
                    with col1:
                        st.write(f"**{expense['purchased']}**")
                    with col2:
                        st.write(f"{expense['amount']:.2f} {expense['currency']}")
                    with col3:
                        st.write(f"{expense['tags']}")
                    with col4:
                        if st.button(f"Readd {expense['purchased']}", key=f"readd_exp_{i}"):
                            results = st.session_state.tracker.add_expenses(expense['amount'], expense['purchased'], expense['tags'], expense['currency'], str(st.session_state.current_month + '-01'), 'Readded from recurring expenses')
                            if results['success']:
                                st.success(results['message'])
                                sync_data()
                                st.rerun()
                            else:
                                st.error(results['message'])
                    st.divider()
        with st.form('add_expenses_form'):
            col1, col2 = st.columns(2)
            with col1:
                expense_purchased = st.text_input('What was purchased?', key='add_exp_purchased')
            with col2:
                expense_amount = st.number_input('Expense Amount', min_value=0.0, step=0.01, key='add_exp_amount')
            expense_category = st.selectbox('Expense Category', options=['Food', 'Transport', 'Entertainment', 'Utilities', 'Bills', 'Other'])
            expense_currency = st.selectbox('Expense Currency', options=['USD', 'EUR', 'JPY', 'GBP', 'AUD', 'CAD', 'CHF', 'CNY', 'SEK', 'NZD', 'THB', 'INR', 'Other'])
            expense_date = st.date_input('Expense Date', key='add_exp_date')
            expense_notes = st.text_area('Expense Notes')
            recurring = st.checkbox('Recurring Expense')
            if st.form_submit_button('Add Expense'):
                if recurring:
                    results = st.session_state.tracker.add_recurring_expense(expense_amount, expense_purchased, expense_category, expense_currency)
                else:
                    results = st.session_state.tracker.add_expenses(expense_amount, expense_purchased, expense_category, expense_currency, str(expense_date), expense_notes)
                if results['success']:
                    st.success(results['message'])
                    sync_data()
                    st.rerun()
                else:
                    st.error(results['message'])
    elif choice == 'Income':
        with st.expander('Recurring Income', expanded=False):
            if not st.session_state.recurring_income:
                st.write("No recurring income found.")
            else:
                for i, income in enumerate(st.session_state.recurring_income):
                    col1, col2, col3 = st.columns([3, 2, 2])
                    with col1:
                        st.write(f"**{income['source']}**")
                    with col2:
                        st.write(f"{income['amount']:.2f} {income['currency']}")
                    with col3:
                        if st.button(f"Readd {income['source']}", key=f"readd_inc_{i}"):
                            results = st.session_state.tracker.add_income(income['amount'], income['source'], str(st.session_state.current_month + '-01'), income['currency'], 'Readded from recurring income')
                            if results['success']:
                                st.success(results['message'])
                                sync_data()
                                st.rerun()
                            else:
                                st.error(results['message'])
                    st.divider()
        with st.form('add_income_form'):
            col1, col2 = st.columns(2)
            with col1:
                income_source = st.text_input('Income Source')
            with col2:
                income_amount = st.number_input('Income Amount', min_value=0.0, step=0.01)
            income_currency = st.selectbox('Income Currency', options=['USD', 'EUR', 'JPY', 'GBP', 'AUD', 'CAD', 'CHF', 'CNY', 'SEK', 'NZD', 'THB', 'INR', 'Other'])
            income_date = st.date_input('Income Date')
            income_notes = st.text_area('Income Notes')
            recurring = st.checkbox('Recurring Income')
            if st.form_submit_button('Add Income'):
                if recurring:
                    results = st.session_state.tracker.add_recurring_income(income_amount, income_source, income_currency)
                else:
                    results = st.session_state.tracker.add_income(income_amount, income_source, str(income_date), income_currency, income_notes)
                if results['success']:
                    st.success(results['message'])
                    sync_data()
                    st.rerun()
                else:
                    st.error(results['message'])
    elif choice == 'Budget':
        with st.form('add_budget_form'):
            budget_amount = st.number_input('Budget Amount', min_value=0.0, step=0.01)
            budget_category = st.selectbox('Budget Category', options=['Food', 'Transport', 'Entertainment', 'Utilities', 'Bills', 'Other'])
            budget_currency = st.selectbox('Budget Currency', options=['USD', 'EUR', 'JPY', 'GBP', 'AUD', 'CAD', 'CHF', 'CNY', 'SEK', 'NZD', 'THB', 'INR', 'Other'])
            if st.form_submit_button('Add Budget'):
                results = st.session_state.tracker.create_budget(budget_category, budget_amount, budget_currency)
                if results['success']:
                    st.success(results['message'])
                    sync_data()
                    st.rerun()
                else:
                    st.error(results['message'])
    elif choice == 'Subscription':
        with st.form('add_subscription_form'):
            subscription_name = st.text_area('Subscription Name')
            subscription_price = st.number_input('Subscription Price', min_value=0.0, step=0.01)
            subscription_currency = st.selectbox('Subscription Currency', options=['USD', 'EUR', 'JPY', 'GBP', 'AUD', 'CAD', 'CHF', 'CNY', 'SEK', 'NZD', 'THB', 'INR', 'Other'])
            subscription_start_date = st.date_input('Start Date')
            if st.form_submit_button('Add Subscription'):
                results = st.session_state.tracker.add_subscriptions(subscription_name, subscription_price, subscription_currency, str(subscription_start_date))
                if results['success']:
                    st.success(results['message'])
                    sync_data()
                    st.rerun()
                else:
                    st.error(results['message'])
    elif choice == 'Goal':
        with st.form('add_goal_form'):
            goal_name = st.text_area('Goal Name')
            goal_target_amount = st.number_input('Goal Target Amount', min_value=0.0, step=0.01)
            goal_monthly_contribution = st.number_input('Monthly Contribution', min_value=0.0, step=0.01)
            goal_start_date = st.date_input('Goal Start Date')
            goal_currency = st.selectbox('Goal Currency', options=['USD', 'EUR', 'JPY', 'GBP', 'AUD', 'CAD', 'CHF', 'CNY', 'SEK', 'NZD', 'THB', 'INR', 'Other'])
            if st.form_submit_button('Add Goal'):
                results = st.session_state.tracker.create_goal(goal_name, goal_target_amount, str(goal_start_date), goal_monthly_contribution, goal_currency)
                if results['success']:
                    st.success(results['message'])
                    sync_data()
                    st.rerun()
                else:
                    st.error(results['message'])

with tab_delete:
    choice = st.selectbox('What to Delete?', options=['Expenses', 'Income', 'Budget', 'Subscription'], key='delete_choice')
    if choice == 'Expenses':
        with st.form('delete_expenses_form'):
            expense_id = st.number_input('Expense ID', min_value=1, step=1)
            if st.form_submit_button('Delete Expense'):
                results = st.session_state.tracker.delete_expenses(expense_id)
                if results['success']:
                    st.success(results['message'])
                    sync_data()
                    st.rerun()
                else:
                    st.error(results['message'])
    elif choice == 'Income':
        with st.form('delete_income_form'):
            income_id = st.number_input('Income ID', min_value=1, step=1)
            if st.form_submit_button('Delete Income'):
                results = st.session_state.tracker.delete_income(income_id)
                if results['success']:
                    st.success(results['message'])
                    sync_data()
                    st.rerun()
                else:
                    st.error(results['message'])
    elif choice == 'Budget':
        with st.form('delete_budget_form'):
            budget_category = st.text_input('Current Budget Category')
            if st.form_submit_button('Delete Budget'):
                results = st.session_state.tracker.delete_budget(budget_category)
                if results['success']:
                    st.success(results['message'])
                    sync_data()
                    st.rerun()
                else:
                    st.error(results['message'])
    elif choice == 'Subscription':
        with st.form('delete_subscription_form'):
            subscription_name = st.text_area('Subscription Name')
            if st.form_submit_button('Delete Subscription'):
                results = st.session_state.tracker.delete_subscription(subscription_name)
                if results['success']:
                    st.success(results['message'])
                    sync_data()
                    st.rerun()
                else:
                    st.error(results['message'])

with tab_edit:
    choice = st.selectbox('What to Edit?', options=['Expenses', 'Income', 'Budget', 'Subscription'], key='edit_choice')
    if choice == 'Expenses':
        with st.form('edit_expenses_form'):
            col1, col2 = st.columns(2)
            with col1:
                expense_id = st.number_input('Expense ID', min_value=1, step=1)
            with col2:
                expense_name = st.text_area('Expense Name')
            expense_amount = st.number_input('Expense Amount', min_value=0.0, step=0.01)
            expense_category = st.selectbox('Expense Category', options=['Food', 'Transport', 'Entertainment', 'Utilities', 'Bills', 'Other'])
            expense_currency = st.selectbox('Expense Currency', options=['USD', 'EUR', 'JPY', 'GBP', 'AUD', 'CAD', 'CHF', 'CNY', 'SEK', 'NZD', 'THB', 'INR', 'Other'])
            expense_date = st.date_input('Expense Date')
            expense_notes = st.text_area('Expense Notes')
            if st.form_submit_button('Edit Expense'):
                results = st.session_state.tracker.edit_expenses(expense_id, expense_amount, expense_name, expense_category, str(expense_date), expense_currency, expense_notes)
                if results['success']:
                    st.success(results['message'])
                    sync_data()
                    st.rerun()
                else:
                    st.error(results['message'])
    elif choice == 'Income':
        with st.form('edit_income_form'):
            col1, col2 = st.columns(2)
            with col1:
                income_id = st.number_input('Income ID', min_value=1, step=1)
            with col2:
                income_name = st.text_area('New Income Name')
            income_amount = st.number_input('Change Income Amount', min_value=0.0, step=0.01)
            income_currency = st.selectbox('Change Income Currency', options=['USD', 'EUR', 'JPY', 'GBP', 'AUD', 'CAD', 'CHF', 'CNY', 'SEK', 'NZD', 'THB', 'INR', 'Other'])
            income_date = st.date_input('Change Income Date')
            income_notes = st.text_area('Update Income Notes')
            if st.form_submit_button('Edit Income'):
                results = st.session_state.tracker.edit_income(income_id, income_amount, income_name, str(income_date), income_currency, income_notes)
                if results['success']:
                    st.success(results['message'])
                    sync_data()
                    st.rerun()
                else:
                    st.error(results['message'])
    elif choice == 'Budget':
        with st.form('edit_budget_form'):
            previous_category = st.text_input('Current Budget Category')
            budget_amount = st.number_input('New Budget Amount', min_value=0.0, step=0.01)
            budget_category = st.selectbox('New Budget Category', options=['Food', 'Transport', 'Entertainment', 'Utilities', 'Bills', 'Other'])
            budget_currency = st.selectbox('Change Budget Currency', options=['USD', 'EUR', 'JPY', 'GBP', 'AUD', 'CAD', 'CHF', 'CNY', 'SEK', 'NZD', 'THB', 'INR', 'Other'])
            if st.form_submit_button('Edit Budget'):
                results = st.session_state.tracker.update_budget(previous_category, budget_category, budget_amount, budget_currency)
                if results['success']:
                    st.success(results['message'])
                    sync_data()
                    st.rerun()
                else:
                    st.error(results['message'])
    elif choice == 'Subscription':
        with st.form('edit_subscription_form'):
            subscription_name = st.text_area('Current Subscription Name')
            subscription_new_name = st.text_input('New Subscription Name (leave blank to keep)')
            subscription_price = st.number_input('Subscription Price', min_value=0.0, step=0.01)
            subscription_currency = st.selectbox('Subscription Currency', options=['USD', 'EUR', 'JPY', 'GBP', 'AUD', 'CAD', 'CHF', 'CNY', 'SEK', 'NZD', 'THB', 'INR', 'Other'])
            if st.form_submit_button('Edit Subscription'):
                results = st.session_state.tracker.edit_subscription(
                    subscription_name,
                    price=subscription_price if subscription_price > 0 else None,
                    name=subscription_new_name if subscription_new_name else None,
                    currency=subscription_currency,
                )
                if results['success']:
                    st.success(results['message'])
                    sync_data()
                    st.rerun()
                else:
                    st.error(results['message'])

with tab_expenses:
    search = st.text_input("Search expenses ...", "", key="expenses_search")
    if search:
        expenses = [expense for expense in st.session_state.expenses if search.lower() in expense['tags'].lower() or search.lower() in (expense['notes'] or '').lower()]
    else:
        expenses = st.session_state.expenses
    if expenses:
        for expense in expenses:
            col1, col2, col3, col4 = st.columns([3, 2, 2, 2])
            with col1:
                st.write(f"**{expense['price']:.2f} {expense['currency'].upper()}**")
            with col2:
                st.write(f"**{expense['tags']}**")
            with col3:
                st.write(f"{expense['date']}")
            with col4:
                st.write(f"{expense['notes'] if expense['notes'] else ''}")
            st.divider()
    elif search:
        st.write(f"No expenses found using search term '{search}'.")
    else:
        st.write("No expenses found. Add expenses to get started.")
    st.file_uploader("Import expenses from .csv", type=["csv"], key="expenses_file_uploader")
    if st.session_state.expenses_file_uploader:
        st.session_state.tracker.import_from_csv("expenses", st.session_state.expenses_file_uploader)
        sync_data()
        st.success("Data imported successfully!")
        st.rerun()
    result = st.session_state.tracker.export_to_csv("expenses", "expenses.csv")
    if result['success']:
        st.download_button(label="Export expenses to .csv", data=result['data'].to_csv(index=False).encode('utf-8'), file_name="expenses.csv", mime="text/csv")

with tab_income:
    search = st.text_input("Search income ...", "", key="income_search")
    if search:
        income_list = [income for income in st.session_state.income if search.lower() in income['source'].lower() or search.lower() in (income['notes'] or '').lower()]
    else:
        income_list = st.session_state.income
    if income_list:
        for income_item in income_list:
            col1, col2, col3, col4 = st.columns([3, 2, 2, 2])
            with col1:
                st.write(f"**{income_item['amount']:.2f} {income_item['currency'].upper()}**")
            with col2:
                st.write(f"**{income_item['source']}**")
            with col3:
                st.write(f"{income_item['date']}")
            with col4:
                st.write(f"{income_item['notes'] if income_item['notes'] else ''}")
            st.divider()
    elif search:
        st.write(f"No income found using search term '{search}'.")
    else:
        st.write("No income found. Add income to get started.")
    st.file_uploader("Import income from .csv", type=["csv"], key="income_file_uploader")
    if st.session_state.income_file_uploader:
        st.session_state.tracker.import_from_csv("income", st.session_state.income_file_uploader)
        sync_data()
        st.success("Data imported successfully!")
        st.rerun()
    result = st.session_state.tracker.export_to_csv("income", "income.csv")
    if result['success']:
        st.download_button(label="Export income to .csv", data=result['data'].to_csv(index=False).encode('utf-8'), file_name="income.csv", mime="text/csv")

with tab_subscriptions:
    search = st.text_input("Search subscriptions ...", "", key="subscriptions_search")
    if search:
        subscriptions = [subscription for subscription in st.session_state.subscriptions if search.lower() in subscription['name'].lower()]
    else:
        subscriptions = st.session_state.subscriptions
    if subscriptions:
        for subscription_item in subscriptions:
            col1, col2 = st.columns([3, 2])
            with col1:
                st.write(f"**{subscription_item['name']}**")
            with col2:
                st.write(f"**{float(subscription_item['price']):.2f} {subscription_item['currency'].upper()}**")
    elif search:
        st.write(f"No subscriptions found using search term '{search}'.")
    else:
        st.write("No subscriptions found. Add subscriptions to get started.")
    st.file_uploader("Import subscriptions from .csv", type=["csv"], key="subscriptions_file_uploader")
    if st.session_state.subscriptions_file_uploader:
        st.session_state.tracker.import_from_csv("subscriptions", st.session_state.subscriptions_file_uploader)
        sync_data()
        st.success("Data imported successfully!")
        st.rerun()
    result = st.session_state.tracker.export_to_csv("subscriptions", "subscriptions.csv")
    if result['success']:
        st.download_button(label="Export subscriptions to .csv", data=result['data'].to_csv(index=False).encode('utf-8'), file_name="subscriptions.csv", mime="text/csv")
