from flask import Flask, render_template
from flask_socketio import SocketIO, emit

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
    return sorted_players[:10]  # Limit to top 10

@socketio.on('register_player')
def handle_register_player(name):
    if not name or get_player(name):
        return
    player = {'name': name, 'scores': [], 'total': 0}
    players.append(player)
    emit('update_player', player, broadcast=True)
    emit('update_leaderboard', update_leaderboard(), broadcast=True)

@socketio.on('add_score')
def handle_add_score(data):
    player = get_player(data['name'])
    if player and len(player['scores']) < 5:
        player['scores'].append(data['score'])
        player['total'] += data['score']
        emit('update_player', player, broadcast=True)
        emit('update_leaderboard', update_leaderboard(), broadcast=True)  # Update leaderboard after each score
        if player['total'] > (max(players, key=lambda x: x['total'], default={'total': 0})['total']):
            emit('new_high_score', broadcast=True)
        if len(player['scores']) == 5:
            # Reset all players when a player completes 5 rounds
            for p in players:
                p['scores'] = []
                p['total'] = 0
            players.clear()  # Remove all players
            emit('reset_all', broadcast=True)
            emit('update_leaderboard', [], broadcast=True)
    elif len(player['scores']) >= 5:
        emit('update_player', player, broadcast=True)

@socketio.on('reset_player')
def handle_reset_player(name):
    player = get_player(name)
    if player:
        player['scores'] = []
        player['total'] = 0
        emit('update_player', player, broadcast=True)
        emit('update_leaderboard', update_leaderboard(), broadcast=True)

@app.route('/')
def index():
    return render_template('index.html')

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5000, debug=True)