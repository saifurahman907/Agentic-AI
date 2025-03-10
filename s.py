import streamlit as st
import mysql.connector
import requests
from twilio.rest import Client
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# MySQL connection
def connect_to_database():
    try:
        db = mysql.connector.connect(
            host="localhost",
            user="root",
            password="",  
            database="shades"
        )
        return db
    except mysql.connector.Error as err:
        st.error(f"Database connection error: {err}")
        return None

# Groq API setup
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"


# Twilio setup
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_PHONE_NUMBER = os.getenv("TWILIO_PHONE_NUMBER")
TWILIO_WHATSAPP_NUMBER = os.getenv("TWILIO_WHATSAPP_NUMBER")
OWNER_PHONE_NUMBER = os.getenv("OWNER_PHONE_NUMBER")

# Initialize Twilio client
twilio_client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)

# Groq API - Answer FAQs
def answer_faq(question):
    # Predefined response for pricing-related queries
    if any(word in question.lower() for word in ["rate", "price", "cost", "charges", "pricing"]):
        return (
            "Thank you for your inquiry! At Shades Cleaning Services, our rates depend on the type of service, "
            "property size, and location. Please provide more details so we can offer an accurate quote!"
        )

    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }
    data = {
        "model": "mixtral-8x7b-32768",
        "messages": [{"role": "user", "content": question}],
        "temperature": 0.7
    }
    try:
        response = requests.post(GROQ_API_URL, headers=headers, json=data)
        if response.status_code == 200:
            return response.json()["choices"][0]["message"]["content"]
        else:
            return f"Error: {response.status_code}, {response.text}"
    except Exception as e:
        return f"Exception: {str(e)}"

# Send SMS
def send_sms(message):
    try:
        twilio_client.messages.create(
            body=message,
            from_=TWILIO_PHONE_NUMBER,
            to=OWNER_PHONE_NUMBER
        )
        st.success("SMS sent successfully!")
    except Exception as e:
        st.error(f"Failed to send SMS: {str(e)}")

# Send WhatsApp message
def send_whatsapp(message):
    try:
        twilio_client.messages.create(
            body=message,
            from_="whatsapp:" + TWILIO_WHATSAPP_NUMBER,
            to="whatsapp:" + OWNER_PHONE_NUMBER
        )
        st.success("WhatsApp message sent successfully!")
    except Exception as e:
        st.error(f"Failed to send WhatsApp message: {str(e)}")

# Streamlit App
def main():
    st.title("Shades Cleaning Services")

    st.sidebar.title("Navigation")
    option = st.sidebar.radio("Choose an option", ["FAQ", "Service Request"])

    if option == "FAQ":
        st.header("FAQ")
        question = st.text_input("Ask a question")
        if st.button("Get Answer"):
            if question:
                answer = answer_faq(question)
                st.success(f"Answer: {answer}")
            else:
                st.warning("Please enter a question.")

    elif option == "Service Request":
        st.header("Service Request")
        customer_name = st.text_input("Name")
        customer_phone = st.text_input("Phone")
        customer_email = st.text_input("Email")
        customer_address = st.text_input("Address")
        service_type = st.selectbox("Service Type", ["Deep Cleaning", "Regular Cleaning", "Carpet Cleaning"])
        date = st.date_input("Date")
        time = st.time_input("Time")

        if st.button("Submit Request"):
            if customer_name and customer_phone and customer_address and service_type and date and time:
                db = connect_to_database()
                if db:
                    cursor = db.cursor()
                    try:
                        # Save customer to database
                        cursor.execute("""
                            INSERT INTO customers (name, phone, email, address)
                            VALUES (%s, %s, %s, %s)
                        """, (customer_name, customer_phone, customer_email, customer_address))
                        db.commit()
                        customer_id = cursor.lastrowid

                        # Save service request to database
                        cursor.execute("""
                            INSERT INTO service_requests (customer_id, service_type, date, time)
                            VALUES (%s, %s, %s, %s)
                        """, (customer_id, service_type, date, time))
                        db.commit()

                        # Send notifications
                        message = (
                            f"New service request: {service_type} for {customer_name} "
                            f"on {date} at {time}. Address: {customer_address}."
                        )
                        send_sms(message)
                        send_whatsapp(message)

                        st.success("Service request received and notifications sent.")
                    except mysql.connector.Error as err:
                        st.error(f"Database error: {err}")
                    finally:
                        cursor.close()
                        db.close()
                else:
                    st.error("Failed to connect to the database.")
            else:
                st.warning("Please fill all the fields.")

# Run the app
if __name__ == "__main__":
    main()
