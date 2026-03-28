import requests

BASE_URL = "http://127.0.0.1:8000"
TOKEN = None


def login():
    global TOKEN
    username = input("Username: ")
    password = input("Password: ")

    res = requests.post(
        BASE_URL + "/auth/login",
        data={"username": username, "password": password}
    )

    data = res.json()
    TOKEN = data["access_token"]
    print("Logged in ✅")


def headers():
    return {"Authorization": f"Bearer {TOKEN}"}


def set_key():
    key = input("Key: ")
    value = input("Value: ")

    res = requests.post(
        BASE_URL + "/kv",
        json={"key": key, "value": value},
        headers=headers()
    )

    print(res.json())


def get_key():
    key = input("Key: ")

    res = requests.get(
        BASE_URL + f"/kv/{key}",
        headers=headers()
    )

    print(res.json())


def delete_key():
    key = input("Key: ")

    res = requests.delete(
        BASE_URL + f"/kv/{key}",
        headers=headers()
    )

    print(res.json())


def menu():
    while True:
        print("\n1. Login")
        print("2. Set Key")
        print("3. Get Key")
        print("4. Delete Key")
        print("5. Exit")

        choice = input("Choice: ")

        if choice == "1":
            login()
        elif choice == "2":
            set_key()
        elif choice == "3":
            get_key()
        elif choice == "4":
            delete_key()
        elif choice == "5":
            break


if __name__ == "__main__":
    menu()