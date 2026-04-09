# Secure Multi-Client Online Quiz System

A secure, real-time online quiz system built using Python low-level sockets and SSL/TLS encryption.

## 🚀 Features
- **Concurrent Clients**: Multiple players can join via terminals simultaneously.
- **SSL/TLS Encryption**: All communication between clients and the server is encrypted using self-signed certificates.
- **Real-Time Leaderboard**: Live ranking updates broadcasted after every question.
- **Fairness & Latency**: Measures and logs client response times and server-side latency.
- **Rich Terminal UI**: ANSI-colored output for questions, results, and rankings.

## 🏗️ Architecture
The system follows a classic **Client-Server architecture**:
1.  **Server**: Central coordinator handling client connections (multi-threaded), quiz timing (synchronized broadcast), and score management (thread-safe).
2.  **Clients**: Securely connect to the server, participate in the quiz, and display live updates.

```
[ Client 1 ] <--- SSL/TLS ---> [ Server ] <--- SSL/TLS ---> [ Client 2 ]
                                  |
                           [ Questions.json ]
```

## 🛠️ Setup & Usage

### 1. Prerequisites
- Python 3.x
- `cryptography` library (used for certificate generation)

### 2. Generate SSL Certificates
The system requires `cert.pem` and `key.pem`. A helper script is provided:
```bash
python gen_cert.py
```

### 3. Run the Server
The server waits for at least 2 players to start the quiz.
```bash
python server.py
```

### 4. Run the Client(s)
Open multiple terminal windows and run:
```bash
python client.py
```

## 📜 Protocol Design
- **Client → Server**:
    - `JOIN|<username>`: Register a new player.
    - `ANSWER|<answer>`: Submit an answer to the current question.
- **Server → Client**:
    - `WELCOME|<username>`: Confirm registration.
    - `QUESTION|<text>|<options>|<timeout>`: Broadcast a new question.
    - `RESULT|CORRECT/WRONG`: Individual feedback for the last answer.
    - `LEADERBOARD|<scores>`: Synchronized ranking update.

## 📈 Performance Evaluation
After the quiz finishes, the server outputs average latency per client and overall system throughput metrics to the terminal and logs them in `logs.txt`.

Example output:
```
Client Alice latency: 120ms
Client Bob latency: 200ms
Average latency: 160ms
```

## 🔒 Security
- Secure socket wrapping via `ssl` module.
- Protection against basic protocol injection through message parsing.
- Thread safety ensured using `threading.Lock`.
