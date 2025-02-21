from flask import Flask, render_template, request, redirect, url_for, session, jsonify

app = Flask(__name__)
app.secret_key = 'your_secret_key'

# 奖池设置
prizes = {
    '一等奖': 0.1,
    '二等奖': 0.2,
    '三等奖': 0.3,
    '谢谢参与': 0.4
}
scratch_count = 100

# 用户数据库（简易版）
users = {
    'user1': 'password1',
    'user2': 'password2'
}

# 用户刮刮乐数量记录
user_scratch_count = {}

@app.route('/')
def index():
    if 'username' not in session:
        return redirect(url_for('login'))
    return render_template('index.html', username=session['username'], scratch_count=scratch_count)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if username in users and users[username] == password:
            session['username'] = username
            if username not in user_scratch_count:
                user_scratch_count[username] = 0
            return redirect(url_for('index'))
        else:
            return '用户名或密码错误'
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('username', None)
    return redirect(url_for('login'))

@app.route('/admin', methods=['GET', 'POST'])
def admin():
    if request.method == 'POST':
        password = request.form['password']
        if password == 'admin123':  # 简易密码
            session['admin'] = True
            return redirect(url_for('admin_settings'))
        else:
            return '密码错误'
    return render_template('admin.html')

@app.route('/admin/settings', methods=['GET', 'POST'])
def admin_settings():
    if 'admin' not in session:
        return redirect(url_for('admin'))
    if request.method == 'POST':
        global prizes, scratch_count
        prizes = {
            '一等奖': float(request.form['first_prize']),
            '二等奖': float(request.form['second_prize']),
            '三等奖': float(request.form['third_prize']),
            '谢谢参与': float(request.form['thanks'])
        }
        scratch_count = int(request.form['scratch_count'])
        return redirect(url_for('admin_settings'))
    return render_template('admin_settings.html', prizes=prizes, scratch_count=scratch_count)

@app.route('/scratch', methods=['POST'])
def scratch():
    if 'username' not in session:
        return '请先登录', 403
    username = session['username']
    if user_scratch_count[username] >= scratch_count:
        return '刮刮乐数量不足', 400
    user_scratch_count[username] += 1
    return '刮刮乐成功', 200

@app.route('/remaining_count')
def remaining_count():
    return jsonify({'remainingCount': scratch_count - sum(user_scratch_count.values())})

if __name__ == '__main__':
    app.run(debug=True)