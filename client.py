import socket
import ssl
import threading
import sys
import time

# Colors for terminal
class Colors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

# Configuration
HOST = 'localhost'
PORT = 5000

def receive_messages(ssl_socket):
    while True:
        try:
            data = ssl_socket.recv(4096).decode('utf-8')
            if not data:
                print(f"{Colors.FAIL}Server disconnected.{Colors.ENDC}")
                break
            
            lines = data.split("\n")
            for line in lines:
                if not line: continue
                
                parts = line.split("|")
                protocol = parts[0]
                
                if protocol == "WELCOME":
                    print(f"\n{Colors.OKGREEN}{Colors.BOLD}--- Welcome to the Secure Quiz, {parts[1]}! ---{Colors.ENDC}")
                    print(f"{Colors.OKCYAN}Waiting for other players to join...{Colors.ENDC}")
                
                elif protocol == "QUESTION":
                    _, text, options_str, timeout = parts
                    options = options_str.split(",")
                    print(f"\n{Colors.HEADER}{Colors.BOLD}QUESTION: {text}{Colors.ENDC}")
                    for i, opt in enumerate(options):
                        print(f"{i+1}. {opt}")
                    print(f"{Colors.WARNING}You have {timeout} seconds! Type your answer.{Colors.ENDC}")
                    print(f"{Colors.BOLD}Your Answer: {Colors.ENDC}", end="", flush=True)
                
                elif protocol == "RESULT":
                    res = parts[1]
                    if res == "CORRECT":
                        print(f"\n{Colors.OKGREEN}{Colors.BOLD}✔ CORRECT!{Colors.ENDC}")
                    else:
                        print(f"\n{Colors.FAIL}{Colors.BOLD}✘ WRONG or TIMEOUT!{Colors.ENDC}")
                
                elif protocol == "LEADERBOARD":
                    print(f"\n{Colors.OKBLUE}{Colors.BOLD}--- Live Leaderboard ---{Colors.ENDC}")
                    scores_raw = parts[1].split(",")
                    for i, entry in enumerate(scores_raw):
                        if entry:
                            user, score = entry.split(":")
                            medal = ""
                            if i == 0: medal = "🥇 "
                            elif i == 1: medal = "🥈 "
                            elif i == 2: medal = "🥉 "
                            print(f"{medal}{i+1}. {user} : {score}")
                    print(f"{Colors.OKBLUE}-----------------------{Colors.ENDC}")
                
                elif protocol == "FINISHED":
                    print(f"\n{Colors.BOLD}{Colors.OKGREEN}QUIZ OVER: {parts[1]}{Colors.ENDC}")
                    sys.exit(0)
                
        except Exception as e:
            print(f"Error receiving data: {e}")
            break

def start_client():
    # Setup SSL context (ignore verification for self-signed demo)
    context = ssl.create_default_context()
    context.check_hostname = False
    context.verify_mode = ssl.CERT_NONE
    
    try:
        raw_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        ssl_socket = context.wrap_socket(raw_socket, server_hostname=HOST)
        ssl_socket.connect((HOST, PORT))
    except Exception as e:
        print(f"{Colors.FAIL}Failed to connect to server: {e}{Colors.ENDC}")
        return

    # User Input for Join
    username = input(f"{Colors.BOLD}Enter your username: {Colors.ENDC}").strip()
    if not username:
        username = "Player"
    
    ssl_socket.send(f"JOIN|{username}\n".encode('utf-8'))
    
    # Start receiver thread
    receiver_thread = threading.Thread(target=receive_messages, args=(ssl_socket,), daemon=True)
    receiver_thread.start()
    
    # Main loop for sending answers
    try:
        while True:
            ans = sys.stdin.readline().strip()
            if ans:
                ssl_socket.send(f"ANSWER|{ans}\n".encode('utf-8'))
    except KeyboardInterrupt:
        print("\nExiting...")
    finally:
        ssl_socket.close()

if __name__ == "__main__":
    start_client()
