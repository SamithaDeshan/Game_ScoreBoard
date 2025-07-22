from flask import Flask, render_template
from flask_socketio import SocketIO, emit
import csv
import os

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")

players = []  # In-memory list: [{'name': str, 'scores': list, 'total': int}]

def get_player(name):
    return next((p for p in players if p['name'] == name), None)

def update_leaderboard():
    if not players:
        return []
    sorted_players = sorted(players, key=lambda x: x['total'], reverse=True)
    rank = 1
    for i in range(len(sorted_players)):
        if i > 0 and sorted_players[i]['total'] == sorted_players[i-1]['total']:
            sorted_players[i]['rank'] = sorted_players[i-1]['rank']
        else:
            sorted_players[i]['rank'] = rank
        rank += 1
    return sorted_players[:10]

def save_to_csv(player):
    file_exists = os.path.isfile('scores.csv')
    with open('scores.csv', 'a', newline='') as file:
        writer = csv.writer(file)
        if not file_exists:
            writer.writerow(['Name', 'Scores', 'Total', 'Completed'])
        writer.writerow([player['name'], ','.join(map(str, player['scores'])), player['total'], player['completed']])

@socketio.on('register_player')
def handle_register_player(name):
    if not name or get_player(name):
        return
    player = {'name': name, 'scores': [], 'total': 0, 'completed': False}
    players.append(player)
    save_to_csv(player)  # Save initial player state
    emit('update_player', player, broadcast=True)
    emit('update_leaderboard', update_leaderboard(), broadcast=True)

@socketio.on('add_score')
def handle_add_score(data):
    player = get_player(data['name'])
    if player and len(player['scores']) < 3 and not player['completed']:
        if data['score'] in [0, 5, 10]:
            player['scores'].append(data['score'])
            player['total'] += data['score']
            save_to_csv(player)  # Save after each score addition
            emit('update_player', player, broadcast=True)
            emit('update_leaderboard', update_leaderboard(), broadcast=True)
            if player['total'] > (max(players, key=lambda x: x['total'], default={'total': 0})['total']):
                emit('new_high_score', {'name': player['name'], 'score': player['total']})
            if len(player['scores']) == 3:
                player['completed'] = True
                save_to_csv(player)  # Save completion state
                if player['total'] > (max(players, key=lambda x: x['total'], default={'total': 0})['total']):
                    emit('new_high_score', {'name': player['name'], 'score': player['total']})
                emit('player_completed', player, broadcast=True)
        else:
            emit('update_player', player, broadcast=True)
    elif len(player['scores']) >= 3:
        emit('update_player', player, broadcast=True)

@socketio.on('reset_player')
def handle_reset_player(name):
    player = get_player(name)
    if player:
        player['scores'] = []
        player['total'] = 0
        player['completed'] = False
        save_to_csv(player)  # Save reset state
        emit('update_player', player, broadcast=True)
        emit('update_leaderboard', update_leaderboard(), broadcast=True)

@socketio.on('add_next_player')
def handle_add_next_player(name):
    if name and not get_player(name):
        player = {'name': name, 'scores': [], 'total': 0, 'completed': False}
        players.append(player)
        save_to_csv(player)  # Save new player state
        emit('update_player', player, broadcast=True)
        emit('update_leaderboard', update_leaderboard(), broadcast=True)

@app.route('/')
def welcome():
    return render_template('welcome.html')

@app.route('/scoreboard')
def scoreboard():
    return render_template('index.html')

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5000, debug=True)