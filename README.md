

# 💬 Chat App
Author: Sakib Hossain Tahmid
* Try my App [Click Here](https://chat-app-sakib12345.streamlit.app/)
<p align="center">
  <img src="https://github.com/sakib-12345/chat-app-with-google-sheet/blob/main/icon.png" alt="Screenshot" width="200">
</p>

* A simple real-time chat web app built with **Python** and **Streamlit**, using **Google Sheets** as the datastore. Users can sign up, log in, chat with others, and admins can ban users and clear messages.

## 🚀 Features

### 👤 User Features
- Sign up & log in  
- Send and receive messages  
- Chat with multiple users  
- Auto-refresh chat feed  

### 🛡️ Admin Features
- Ban & unban users  
- Clear full chat history  
- View all users  
- Manage messages  

### 🔑 Security Features
- Passwords are fully encrypted before being stored in the database.
- End-to-end encrypted chat can be enabled using Python’s **hash** libraries.
- Passwords remain inaccessible even to database administrators.


## 🛠️ Tech Stack
- **Python**
- **Streamlit**
- **Google Sheets (gspread)**

## 📊 Database Setup
- **Step 1:** Create a Google sheet.
- **Step 2:** There will be three different sheet named users, messeges and banned.
- **Step 3:** Columns must be:
  - users: **| username | password | role |**
  - messeges: **| username | role | content | timestamp |**
  - banned: **| username |**
- **Step 4:** Add google service account email in the sheet(as a editor)    
- **Step 5:** Copy the API configuration file and convert it into a TOML-style format. Keep this file strictly confidential.
- **Step 6:** Use the file as your environment variable configuration.
- **Step 7:** Deploy the application to any Python-compatible server.


"IN MY CASE, I USE STREAMLIT FREE SERVER AND PASTE THE API KEY IN STREAMLIT SECRETS."

## 🔧 Setup

#### 1.Clone
```bash
https://github.com/sakib-12345/chat-app-with-google-sheet.git
```
#### 2.Open folder
```bash
cd chat-app-with-google-sheet
```
#### 3.Install Libraries
```bash
pip install -r requirements.txt
```
#### 4.Run it (Locally)
```bash
streamlit run chat.py
```
## License
- This project is licensed under the MIT License. You can use, copy, and modify it freely as long as you include the original license.
