import socket
import ssl
import threading
import json
import time
import logging
from datetime import datetime

# Configuration
HOST = 'localhost'
PORT = 5000
CERT_FILE = 'cert.pem'
KEY_FILE = 'key.pem'
QUESTIONS_FILE = 'questions.json'
LOG_FILE = 'logs.txt'
QUESTION_TIMEOUT = 10  # seconds
MIN_PLAYERS = 2

# Logging setup
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler()
    ]
)

# Shared data structures
clients = []
client_names = {}  # socket: username
scores = {}        # username: score
client_latencies = {} # username: [latencies]
locks = threading.Lock()
quiz_started = threading.Event()
current_question_index = -1
answers_received = {} # username: (answer, timestamp)
question_start_time = 0

def load_questions():
    try:
        with open(QUESTIONS_FILE, 'r') as f:
            return json.load(f)
    except Exception as e:
        logging.error(f"Failed to load questions: {e}")
        return []

def broadcast(message):
    with locks:
        for client in clients:
            try:
                client.send((message + "\n").encode('utf-8'))
            except Exception as e:
                logging.error(f"Broadcast error to a client: {e}")

def get_leaderboard_str():
    with locks:
        sorted_scores = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        return ",".join([f"{user}:{score}" for user, score in sorted_scores])

def handle_client(conn, addr):
    global clients, scores, client_names
    username = "Unknown"
    
    try:
        # Initial greeting and JOIN
        data = conn.recv(1024).decode('utf-8').strip()
        if data.startswith("JOIN|"):
            username = data.split("|")[1]
            with locks:
                if username in scores:
                    username = f"{username}_{addr[1]}" # Avoid duplicates
                client_names[conn] = username
                scores[username] = 0
                client_latencies[username] = []
                clients.append(conn)
            
            conn.send(f"WELCOME|{username}\n".encode('utf-8'))
            logging.info(f"User {username} joined from {addr}")
            
            # Broadcast current leaderboard to the new joiner
            conn.send(f"LEADERBOARD|{get_leaderboard_str()}\n".encode('utf-8'))
            
            # Wait for quiz to start or next question
            while True:
                data = conn.recv(1024).decode('utf-8').strip()
                if not data:
                    break
                
                if data.startswith("ANSWER|"):
                    answer = data.split("|")[1]
                    timestamp = time.time()
                    with locks:
                        if username not in answers_received:
                            answers_received[username] = (answer, timestamp)
                            latency = (timestamp - question_start_time) * 1000 # ms
                            client_latencies[username].append(latency)
                            logging.info(f"Received answer from {username} in {latency:.2f}ms")
                
    except Exception as e:
        logging.error(f"Error handling client {username}: {e}")
    finally:
        with locks:
            if conn in clients:
                clients.remove(conn)
            if conn in client_names:
                del client_names[conn]
        conn.close()
        logging.info(f"Client {username} disconnected")

def quiz_engine():
    global current_question_index, answers_received, question_start_time
    questions = load_questions()
    
    logging.info(f"Waiting for at least {MIN_PLAYERS} players to start...")
    while len(clients) < MIN_PLAYERS:
        time.sleep(1)
    
    logging.info("Minimum players reached. Starting quiz in 5 seconds...")
    time.sleep(5)
    quiz_started.set()
    
    for i, q in enumerate(questions):
        current_question_index = i
        options_str = ",".join(q['options'])
        
        # Reset current answers
        with locks:
            answers_received = {}
            question_start_time = time.time()
        
        # Broadcast QUESTION|question|options|time
        broadcast(f"QUESTION|{q['question']}|{options_str}|{QUESTION_TIMEOUT}")
        
        # Wait for timeout
        time.sleep(QUESTION_TIMEOUT)
        
        # Evaluate answers
        with locks:
            correct_answer = q['answer']
            for user, (ans, timestamp) in answers_received.items():
                if ans.strip().lower() == correct_answer.strip().lower():
                    scores[user] += 10
                    # Find conn and send result
                    for conn, name in client_names.items():
                        if name == user:
                            try:
                                conn.send("RESULT|CORRECT\n".encode('utf-8'))
                            except: pass
                else:
                    for conn, name in client_names.items():
                        if name == user:
                            try:
                                conn.send("RESULT|WRONG\n".encode('utf-8'))
                            except: pass
            
            # For those who didn't answer
            for user in scores:
                if user not in answers_received:
                    for conn, name in client_names.items():
                        if name == user:
                            try:
                                conn.send("RESULT|WRONG\n".encode('utf-8'))
                            except: pass

        # Broadcast Leaderboard
        broadcast(f"LEADERBOARD|{get_leaderboard_str()}")
        time.sleep(2) # Gap between questions

    # Final stats
    logging.info("Quiz finished. Printing performance evaluation.")
    print("\n--- Performance Evaluation ---")
    total_latency = 0
    count = 0
    for user, latencies in client_latencies.items():
        if latencies:
            avg = sum(latencies) / len(latencies)
            print(f"Client {user} average latency: {avg:.2f}ms")
            total_latency += sum(latencies)
            count += len(latencies)
        else:
            print(f"Client {user} latency: N/A")
    
    if count > 0:
        print(f"Average system latency: {total_latency/count:.2f}ms")
    
    broadcast("FINISHED|Quiz completed!")
    time.sleep(5)
    # Could potentially close server or restart

def start_server():
    # Setup SSL context
    context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
    context.load_cert_chain(certfile=CERT_FILE, keyfile=KEY_FILE)
    
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_socket.bind((HOST, PORT))
    server_socket.listen(5)
    
    logging.info(f"Server listening on {HOST}:{PORT}")
    
    # Start quiz engine in a separate thread
    engine_thread = threading.Thread(target=quiz_engine, daemon=True)
    engine_thread.start()
    
    try:
        while True:
            client_conn, addr = server_socket.accept()
            try:
                ssl_conn = context.wrap_socket(client_conn, server_side=True)
                client_thread = threading.Thread(target=handle_client, args=(ssl_conn, addr), daemon=True)
                client_thread.start()
            except ssl.SSLError as e:
                logging.error(f"SSL Handshake failed: {e}")
                client_conn.close()
    except KeyboardInterrupt:
        logging.info("Server shutting down...")
    finally:
        server_socket.close()

if __name__ == "__main__":
    start_server()
