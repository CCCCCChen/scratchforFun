import os
import json
import random
import sqlite3

from flask import Flask, render_template, request, redirect, url_for, session, jsonify

app = Flask(__name__)
app.secret_key = 'your_secret_key'

# 在 Flask 应用中注册 random 模块为全局变量
app.jinja_env.globals.update(random=random)

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

# 初始化判断逻辑
def initialize_app():
    db_file = 'xx.sqlite'
    if not os.path.exists(db_file):
        print("初始化逻辑开始...")
        
        # 1. 获取 setting.json 的内容
        try:
            with open('setting.json', 'r', encoding='utf-8') as f:
                settings = json.load(f)
                total_tickets = settings.get('total_tickets', 100)
                total_amount = settings.get('total_amount', 10000)
                prize_amounts = settings.get('prize_amounts', [10, 20, 30, 50, 100, 200, 500, 1000])
                target_winning_tickets = settings.get('target_winning_tickets', 50)
        except FileNotFoundError:
            print("setting.json 文件未找到，使用默认值")
            total_tickets = 100
            total_amount = 10000
            prize_amounts = [10, 20, 30, 50, 100, 200, 500, 1000]
            target_winning_tickets = 50
        
        # 2. 根据总票数、总金额、可中奖金额列表和目标中奖票数，生成中奖金额频数列表
        def generate_prize_frequencies(total_tickets, total_amount, prize_amounts, target_winning_tickets):
            prize_frequencies = [1] * len(prize_amounts)  # 修改：初始值设为1
            remaining_tickets = target_winning_tickets - len(prize_amounts)  # 修改：减去已分配的票数
            remaining_amount = total_amount - sum(prize_amounts)  # 修改：减去已分配的金额
            
            # 随机分配剩余的中奖票数
            for i in range(len(prize_amounts) - 1, 0, -1):
                max_possible = min(remaining_tickets, remaining_amount // prize_amounts[i])
                if max_possible > 0:  # 确保 max_possible 大于 0
                    prize_frequencies[i] += random.randint(0, max_possible)  # 修改：累加分配的票数
                    remaining_tickets -= prize_frequencies[i] - 1  # 修改：减去已分配的票数
                    remaining_amount -= prize_frequencies[i] * prize_amounts[i]  # 修改：减去已分配的金额
            
            # 分配剩余的中奖票数
            prize_frequencies[0] += remaining_tickets  # 修改：累加分配的票数
            
            # 调整以确保总金额匹配
            while remaining_amount > 0:
                for i in range(len(prize_amounts)):
                    if remaining_amount >= prize_amounts[i]:
                        prize_frequencies[i] += 1
                        remaining_amount -= prize_amounts[i]
            
            return prize_frequencies
        
        prize_frequencies = generate_prize_frequencies(total_tickets, total_amount, prize_amounts, target_winning_tickets)
        print(f"生成的中奖金额频数列表: {prize_frequencies}")
        
        # 3. 创建数据库并保存中奖金额频数
        conn = sqlite3.connect(db_file)
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS prizes (
                id INTEGER PRIMARY KEY,
                amount REAL,
                frequency INTEGER
            )
        ''')
        for i, freq in enumerate(prize_frequencies):
            cursor.execute('INSERT INTO prizes (amount, frequency) VALUES (?, ?)', (prize_amounts[i], freq))
        conn.commit()
        
        # 添加创建 users 表的逻辑
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY,
                username TEXT UNIQUE,
                password TEXT,
                spent_amount REAL DEFAULT 0
            )
        ''')
        conn.commit()
        
        # 4. 随机生成中奖票数个不重复的整数列表
        winning_ticket_indices = random.sample(range(1, total_tickets + 1), target_winning_tickets)
        
        # 5. 生成票编号并初始化金额和状态
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS tickets (
                id INTEGER PRIMARY KEY,
                ticket_number TEXT,
                amount REAL,
                is_selected INTEGER DEFAULT 0
            )
        ''')
        for i in range(1, total_tickets + 1):
            ticket_number = f"94-1219-00000010-{i:03d}"
            amount = 0
            if i in winning_ticket_indices:
                prize_index = random.randint(0, len(prize_amounts) - 1)
                amount = prize_amounts[prize_index]
                prize_frequencies[prize_index] -= 1
            cursor.execute('INSERT INTO tickets (ticket_number, amount) VALUES (?, ?)', (ticket_number, amount))
        conn.commit()
        
        conn.close()
        print("初始化完成。")
    else:
        print("已存在初始化文件，跳过初始化逻辑。")

# 应用启动时调用初始化函数
initialize_app()

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
            
            # 初始化用户信息（从数据库读取）
            conn = sqlite3.connect('xx.sqlite')
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM users WHERE username = ?', (username,))
            user_info = cursor.fetchone()
            conn.close()
            
            if user_info:
                session['spent_amount'] = user_info[3]  # 假设数据库中第四列为花费金额
            else:
                session['spent_amount'] = 0
            
            return redirect(url_for('dashboard'))  # 登录后跳转到日历卡片页面
        else:
            return '用户名或密码错误'
    return render_template('login.html')

@app.route('/dashboard')
def dashboard():
    if 'username' not in session:
        return redirect(url_for('login'))
    
    # 查询未被选中的票
    conn = sqlite3.connect('xx.sqlite')
    cursor = conn.cursor()
    cursor.execute('SELECT id, ticket_number FROM tickets WHERE is_selected = 0 ORDER BY id')
    tickets = cursor.fetchall()
    conn.close()
    
    # 分页逻辑
    page = int(request.args.get('page', 1))
    per_page = 9  # 每页显示9张票
    start = (page - 1) * per_page
    end = start + per_page
    tickets_on_page = tickets[start:end]
    
    return render_template('dashboard.html', tickets=tickets_on_page, page=page)

@app.route('/scratch_card/<int:ticket_id>')
def scratch_card(ticket_id):
    if 'username' not in session:
        return redirect(url_for('login'))
    
    # 更新票的状态为已选中
    conn = sqlite3.connect('xx.sqlite')
    cursor = conn.cursor()
    cursor.execute('UPDATE tickets SET is_selected = 1 WHERE id = ?', (ticket_id,))
    conn.commit()
    
    # 查询票的详细信息
    cursor.execute('SELECT ticket_number, amount FROM tickets WHERE id = ?', (ticket_id,))
    ticket_info = cursor.fetchone()
    conn.close()
    
    if ticket_info:
        ticket_number, amount = ticket_info
        return render_template('scratch_card.html', ticket_number=ticket_number, amount=amount)
    else:
        return '票不存在', 404

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if username in users:
            return '用户名已存在'
        users[username] = password
        return redirect(url_for('login'))
    return render_template('register.html')

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