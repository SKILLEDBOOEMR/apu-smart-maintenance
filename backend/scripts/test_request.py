import requests

url = "http://127.0.0.1:8000/analyze"
base_url = "http://127.0.0.1:8000"

def the_correct_request(uuid=None):
    # Path to an image file on your laptop
    image_path = "backend/test_files/images (10).jfif"

    # Your test data dictionary
    data = {
        "text": "Leaking in the room",
        "building": "Tower B",
        "room": "2",
        "latitude": "3.055305",  # Form fields come through as strings/values
        "longitude": "101.699984",
        "uuid": uuid,
    }

    with open(image_path, "rb") as f:
        files = {"image": ("image.jpg", f, "image/jpeg")}
        response = requests.post(url, data=data, files=files)

    print("Status Code:", response.status_code)
    print("Response JSON:", response.json())

def no_image_request():
    data = {
        "text": "Leaking in the room",
        "building": "Tower B",
        "room": "2",
        "latitude": 3.055305,
        "longitude": 101.699984,
    }

    response = requests.post(url, data=data)
    print("Status Code:", response.status_code)
    print("Response JSON:", response.json())

def invalid_location_request():
    image_path = "backend/test_files/images (3).jfif"

    data = {
        "text": "Leaking in the room",
        "building": "Tower B",
        "room": "2",
        "latitude": 3.000000,  # Invalid latitude
        "longitude": 101.000000,  # Invalid longitude
    }

    with open(image_path, "rb") as f:
        files = {"image": ("image.jpg", f, "image/jpeg")}
        response = requests.post(url, data=data, files=files)

    print("Status Code:", response.status_code)
    print("Response JSON:", response.json())

def just_regular_picture_nothing_wrong():
    image_path = "backend/test_files/images (9).jfif"

    data = {
        "text": "There is a pipe leaking!",
        "building": "Tower B",
        "room": "2",
        "latitude": 3.055305,
        "longitude": 101.699984,
    }

    with open(image_path, "rb") as f:
        files = {"image": ("image.jpg", f, "image/jpeg")}
        response = requests.post(url, data=data, files=files)

    print("Status Code:", response.status_code)
    print("Response JSON:", response.json())

def test_signup(admin=False, email=None, password=None, full_name=None):
    test_email = email if email else "deenub123@gmail.com"
    test_password = password if password else "securepassword123"
    test_full_name = full_name if full_name else "Python Test User"

    # 1. Test Signup Endpoint
    print("Testing /signup...")
    signup_payload = {
        "email": test_email,
        "password": test_password,
        "full_name": test_full_name,
        "role": "admin" if admin else "user"
    }
    
    try:
        response = requests.post(f"{base_url}/signup", json=signup_payload)
        print(f"Signup Status: {response.status_code}")
        print(f"Signup Response: {response.json()}")
    except Exception as e:
        print(f"Signup failed to connect: {e}")
        return
    
def test_login():
    test_email = "warrenwinarko@gmail.com"
    test_password = "securepassword123"

    # 2. Test Login Endpoint
    print("\nTesting /login...")
    login_payload = {
        "email": test_email,
        "password": test_password
    }
    
    try:
        response = requests.post(f"{base_url}/login", json=login_payload)
        print(f"Login Status: {response.status_code}")
        print(f"Login Response: {response.json()}")
    except Exception as e:
        print(f"Login failed to connect: {e}")

def test_login_report_checkduplicate():
    test_email = "deenub123@gmail.com"
    test_password = "securepassword123"

    print("\nTesting /login...")
    login_payload = {
        "email": test_email,
        "password": test_password
    }
    
    try:
        response = requests.post(f"{base_url}/login", json=login_payload)
        print(f"Login Status: {response.status_code}")
        print(f"Login Response: {response.json()}")
        
        # Ensure login was successful before proceeding
        if response.status_code != 200:
            print("❌ Login failed with non-200 status code.")
            return

        response_data = response.json()
        user_id = response_data.get("user_id")
        
        if not user_id:
            print("❌ Error: 'auth_user_id' not found in login response payload.")
            return
            
        print(f"Extracted User ID: {user_id}")
        the_correct_request(uuid=user_id)  # Pass the user_id safely

    except requests.exceptions.RequestException as e:
        print(f"❌ Login failed to connect: {e}")
    except Exception as e:
        print(f"❌ An unexpected error occurred: {e}")

def test_login_fetch_own_reports():
    test_email = "deenub123@gmail.com"
    test_password = "securepassword123"

    print("\nTesting /login...")
    login_payload = {
        "email": test_email,
        "password": test_password
    }
    
    try:
        response = requests.post(f"{base_url}/login", json=login_payload)
        print(f"Login Status: {response.status_code}")
        print(f"Login Response: {response.json()}")
        
        # Ensure login was successful before proceeding
        if response.status_code != 200:
            print("❌ Login failed with non-200 status code.")
            return

        response_data = response.json()
        user_id = response_data.get("user_id")
        
        if not user_id:
            print("❌ Error: 'auth_user_id' not found in login response payload.")
            return
            
        print(f"Extracted User ID: {user_id}")
        fetch_own_orders = requests.get(f"{base_url}/requests/mine", params={"student_id": user_id})
        print(f"Fetch Own Reports Status: {fetch_own_orders.status_code}")
        print(f"Fetch Own Reports Response: {fetch_own_orders.json()}")

    except requests.exceptions.RequestException as e:
        print(f"❌ Login failed to connect: {e}")
    except Exception as e:
        print(f"❌ An unexpected error occurred: {e}")

def admin_fetch_work_orders():
    test_email = "admin@example.com"
    test_password = "adminpassword"

    print("\nTesting /login...")
    login_payload = {
        "email": test_email,
        "password": test_password
    }

    try:
        response = requests.post(f"{base_url}/login", json=login_payload)
        print(f"Login Status: {response.status_code}")
        print(f"Login Response: {response.json()}")

        # Ensure login was successful before proceeding
        if response.status_code != 200:
            print("❌ Login failed with non-200 status code.")
            return

        response_data = response.json()
        user_id = response_data.get("user_id")

        if not user_id:
            print("❌ Error: 'auth_user_id' not found in login response payload.")
            return

        print(f"Extracted User ID: {user_id}")
        fetch_work_orders = requests.get(f"{base_url}/work-orders", params={"uuid": user_id})
        print(f"Fetch Work Orders Status: {fetch_work_orders.status_code}")
        print(f"Fetch Work Orders Response: {fetch_work_orders.json()}")

    except requests.exceptions.RequestException as e:
        print(f"❌ Login failed to connect: {e}")
    except Exception as e:
        print(f"❌ An unexpected error occurred: {e}")

def admin_fetch_specific_work_orders():
    test_email = "admin@example.com"
    test_password = "adminpassword"

    print("\nTesting /login...")
    login_payload = {
        "email": test_email,
        "password": test_password
    }

    try:
        response = requests.post(f"{base_url}/login", json=login_payload)
        print(f"Login Status: {response.status_code}")
        print(f"Login Response: {response.json()}")

        # Ensure login was successful before proceeding
        if response.status_code != 200:
            print("❌ Login failed with non-200 status code.")
            return

        response_data = response.json()
        user_id = response_data.get("user_id")

        if not user_id:
            print("❌ Error: 'auth_user_id' not found in login response payload.")
            return

        print(f"Extracted User ID: {user_id}")
        fetch_work_orders = requests.get(f"{base_url}/work-orders", params={"uuid": user_id})
        print(f"Fetch Work Orders Status: {fetch_work_orders.status_code}")
        print(f"Fetch Work Orders Response: {fetch_work_orders.json()}")

        specific_work_order_id = fetch_work_orders.json().get("work_orders")[0].get("id") if fetch_work_orders.json() else None
        fetch_specific_work_order = requests.get(f"{base_url}/work-orders/{specific_work_order_id}", params={"uuid": user_id})
        print(f"Fetch Specific Work Order Status: {fetch_specific_work_order.status_code}")
        print(f"Fetch Specific Work Order Response: {fetch_specific_work_order.json()}")

    except requests.exceptions.RequestException as e:
        print(f"❌ Login failed to connect: {e}")
    except Exception as e:
        print(f"❌ An unexpected error occurred: {e}")

def admin_notify_work_order(work_order_id):
    test_email = "admin@example.com"
    test_password = "adminpassword"

    print("\nTesting /login...")
    login_payload = {
        "email": test_email,
        "password": test_password
    }

    try:
        response = requests.post(f"{base_url}/login", json=login_payload)
        print(f"Login Status: {response.status_code}")
        print(f"Login Response: {response.json()}")

        # Ensure login was successful before proceeding
        if response.status_code != 200:
            print("❌ Login failed with non-200 status code.")
            return

        response_data = response.json()
        user_id = response_data.get("user_id")

        if not user_id:
            print("❌ Error: 'auth_user_id' not found in login response payload.")
            return

        print(f"Extracted User ID: {user_id}")
        payload = {"uuid": user_id, "work_order_id": work_order_id}
        print("DEBUG - Sending Payload:", payload)  # Check what prints here!

        response = requests.post(
            f"{base_url}/work-orders/{work_order_id}/notify", 
            json=payload
        )
        print(f"Notify Work Order Status: {response.status_code}")
        print(f"Notify Work Order Response: {response.json()}")

    except requests.exceptions.RequestException as e:
        print(f"❌ Login failed to connect: {e}")
    except Exception as e:
        print(f"❌ An unexpected error occurred: {e}")

if __name__ == "__main__":
    # print("----- Correct Request -----")
    # the_correct_request()
    # print("\n----- No Image Request -----")
    # no_image_request()
    # print("\n----- Invalid Location Request -----")
    # invalid_location_request()
    # print("\n----- Just Regular Picture, Nothing Wrong -----")
    # just_regular_picture_nothing_wrong()
    # print("\n----- Testing Signup -----")
    # test_signup()

    # print("\n----- Testing Login -----")
    # test_login()
    # print("\n----- Testing Login and Report -----")
    # test_login_report_checkduplicate()
    # print("\n----- Testing Login and Fetch Own Reports -----")
    # test_login_fetch_own_reports()
    # print("\n----- Testing Signup with Admin Role -----")
    # test_signup(admin=True,email='admin@example.com', password='adminpassword', full_name='Admin User')
    # print("\n----- Testing Admin Fetch Work Orders -----")
    # admin_fetch_work_orders()
    # print("\n----- Testing Admin Fetch Specific Work Orders -----")
    # admin_fetch_specific_work_orders()
    print("\n----- Testing Admin Notify Work Order -----")
    admin_notify_work_order(work_order_id="174eeaca-abde-4e64-b767-53dc1cb2676a")  # Replace with an actual work order ID
    pass