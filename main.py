import os

def run_agent():
    os.system('python agent.py')

def run_server():
    os.system('python server.py')

if __name__ == "__main__":
    print("Choose a role to start:")
    print("1. Agent")
    print("2. Server")
    choice = input("Enter your choice (1 or 2): ")

    if choice == '1':
        run_agent()
    elif choice == '2':
        run_server()
    else:
        print("Invalid choice. Please restart the program and choose 1 or 2.")

