import json
import os
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

# 从数据库获取用户信息的函数
def get_user_from_db(username):
    try:
        conn = sqlite3.connect('xx.sqlite')
        cursor = conn.cursor()
        cursor.execute('SELECT username, password FROM users WHERE username = ?', (username,))
        user = cursor.fetchone()
        conn.close()
        return user
    except sqlite3.Error as e:
        print(f"获取用户信息错误: {e}")
        return None

# 用户刮刮乐数量记录
user_scratch_count = {}

# 根据总票数、总金额、可中奖金额列表和目标中奖票数，生成中奖金额频数列表
def generate_prize_frequencies(prize_amounts, target_winning_tickets, total_amount):
    """
    使用动态规划算法生成奖项频率分配，优化中间奖项分配
    减少最大奖和最小奖的数量，增加中间奖的数量
    """
    # 输入验证
    if target_winning_tickets <= 0 or total_amount <= 0:
        return [0] * len(prize_amounts)
    
    # 计算中间奖项的权重策略
    n = len(prize_amounts)
    if n <= 2:
        # 如果奖项太少，使用原始排序
        prize_with_idx = [(i, amount) for i, amount in enumerate(prize_amounts)]
    else:
        # 创建权重映射，中间奖项权重更高
        weights = []
        for i, amount in enumerate(prize_amounts):
            if i == 0 or i == n - 1:  # 最小奖和最大奖
                weight = 0.3  # 降低权重
            elif i == 1 or i == n - 2:  # 次小奖和次大奖
                weight = 0.7
            else:  # 中间奖项
                weight = 1.0  # 最高权重
            weights.append((i, amount, weight))
        
        # 按权重和奖金综合排序，优先选择中间奖项
        prize_with_idx = sorted(weights, key=lambda x: (-x[2], x[1]))
        prize_with_idx = [(idx, amount) for idx, amount, _ in prize_with_idx]
    
    # dp[i][j] 表示是否能用 j 张票凑出金额 i
    dp = [[False] * (target_winning_tickets + 1) for _ in range(total_amount + 1)]
    dp[0][0] = True
    
    # prev[i][j] 记录到达金额 i 使用 j 张票时的最后一个奖项索引
    prev = [[None] * (target_winning_tickets + 1) for _ in range(total_amount + 1)]
    
    # 动态规划填充，优先使用权重高的奖项
    for amount in range(1, total_amount + 1):
        for tickets in range(1, target_winning_tickets + 1):
            for prize_idx, prize_amount in prize_with_idx:
                if prize_amount <= amount and dp[amount - prize_amount][tickets - 1]:
                    dp[amount][tickets] = True
                    prev[amount][tickets] = prize_idx
                    break  # 找到即可停止
    
    # 寻找最优解（尽可能使用目标票数）
    best_tickets = 0
    best_amount = 0
    
    for tickets in range(target_winning_tickets, 0, -1):
        for amount in range(total_amount, 0, -1):
            if dp[amount][tickets]:
                best_tickets = tickets
                best_amount = amount
                break
        if best_tickets > 0:
            break
    
    # 如果找不到解，返回空分配
    if best_tickets == 0:
        return [0] * len(prize_amounts)
    
    # 回溯构建奖项分配
    prize_frequencies = [0] * len(prize_amounts)
    current_amount = best_amount
    current_tickets = best_tickets
    
    while current_tickets > 0 and current_amount > 0:
        last_prize_idx = prev[current_amount][current_tickets]
        if last_prize_idx is None:
            break
        
        prize_frequencies[last_prize_idx] += 1
        current_amount -= prize_amounts[last_prize_idx]
        current_tickets -= 1
    
    # 后处理：进一步优化分配，减少极值奖项
    prize_frequencies = optimize_prize_distribution(prize_frequencies, prize_amounts, target_winning_tickets, total_amount)
    
    print(f"优化后分配结果: 使用 {sum(prize_frequencies)} 张票，总金额 {sum(f * prize_amounts[i] for i, f in enumerate(prize_frequencies))} 元")
    for i, freq in enumerate(prize_frequencies):
        if freq > 0:
            print(f"奖项 {prize_amounts[i]} 元: {freq} 张")
    
    return prize_frequencies

def optimize_prize_distribution(frequencies, prize_amounts, target_tickets, total_amount):
    """
    后处理优化：减少最大奖和最小奖的数量，增加中间奖
    """
    n = len(prize_amounts)
    if n <= 2:
        return frequencies
    
    optimized = frequencies.copy()
    max_iterations = 10  # 防止无限循环
    
    for _ in range(max_iterations):
        # 找到最小奖和最大奖的索引
        min_idx = 0
        max_idx = n - 1
        
        # 如果最小奖或最大奖数量过多，尝试转换为中间奖
        total_extreme = optimized[min_idx] + optimized[max_idx]
        total_middle = sum(optimized[1:n-1])
        
        if total_extreme > total_middle and total_extreme > 2:
            # 尝试将一个极值奖转换为中间奖
            if optimized[min_idx] > 0 and optimized[max_idx] > 0:
                # 选择数量更多的极值奖进行转换
                source_idx = min_idx if optimized[min_idx] >= optimized[max_idx] else max_idx
            elif optimized[min_idx] > 0:
                source_idx = min_idx
            elif optimized[max_idx] > 0:
                source_idx = max_idx
            else:
                break
            
            # 寻找合适的中间奖项进行替换
            source_amount = prize_amounts[source_idx]
            for target_idx in range(1, n-1):  # 中间奖项
                target_amount = prize_amounts[target_idx]
                
                # 计算可以转换的数量
                if source_amount > target_amount:
                    # 一个大奖可以换多个小奖
                    ratio = source_amount // target_amount
                    if ratio > 1 and optimized[source_idx] > 0:
                        # 检查是否超出票数限制
                        additional_tickets = ratio - 1
                        current_total_tickets = sum(optimized)
                        if current_total_tickets + additional_tickets <= target_tickets:
                            optimized[source_idx] -= 1
                            optimized[target_idx] += ratio
                            break
                elif source_amount < target_amount:
                    # 多个小奖可以换一个大奖
                    ratio = target_amount // source_amount
                    if ratio > 1 and optimized[source_idx] >= ratio:
                        # 检查票数是否足够
                        reduced_tickets = ratio - 1
                        optimized[source_idx] -= ratio
                        optimized[target_idx] += 1
                        break
        else:
            break  # 分配已经比较均衡
    
    return optimized

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
        
        prize_frequencies = generate_prize_frequencies(prize_amounts, target_winning_tickets, total_amount)
        print(f"生成的中奖金额频数列表: {prize_frequencies}")
        
        # 3. 创建数据库并保存中奖金额频数
        try:
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
        except sqlite3.Error as e:
            print(f"数据库操作错误: {e}")
            if 'conn' in locals():
                conn.rollback()
        finally:
            if 'conn' in locals():
                conn.close()
        
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
            
            # 创建奖金池用于分配
            prize_pool = []
            for i, freq in enumerate(prize_frequencies):
                prize_pool.extend([prize_amounts[i]] * freq)
            random.shuffle(prize_pool)
            
            prize_index = 0
            for i in range(1, total_tickets + 1):
                ticket_number = f"94-1219-00000010-{i:03d}"
                amount = 0
                if i in winning_ticket_indices and prize_index < len(prize_pool):
                    amount = prize_pool[prize_index]
                    prize_index += 1
                cursor.execute('INSERT INTO tickets (ticket_number, amount) VALUES (?, ?)', (ticket_number, amount))
            
            # 初始化默认用户到数据库
            default_users = [
                ('user1', 'password1'),
                ('user2', 'password2')
            ]
            for username, password in default_users:
                try:
                    cursor.execute('INSERT INTO users (username, password) VALUES (?, ?)', (username, password))
                except sqlite3.IntegrityError:
                    # 用户已存在，跳过
                    pass
            conn.commit()
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
        
        # 从数据库验证用户
        user = get_user_from_db(username)
        if user and user[1] == password:  # user[1] 是密码
            session['username'] = username
            if username not in user_scratch_count:
                user_scratch_count[username] = 0
            
            # 初始化用户信息（从数据库读取）
            try:
                conn = sqlite3.connect('xx.sqlite')
                cursor = conn.cursor()
                cursor.execute('SELECT * FROM users WHERE username = ?', (username,))
                user_info = cursor.fetchone()
                conn.close()
                
                if user_info:
                    session['spent_amount'] = user_info[3]  # 数据库中第四列为花费金额
                else:
                    session['spent_amount'] = 0
            except sqlite3.Error as e:
                print(f"读取用户信息错误: {e}")
                session['spent_amount'] = 0
            
            return redirect(url_for('dashboard'))  # 登录后跳转到日历卡片页面
        else:
            return '用户名或密码错误'
    return render_template('login.html')

@app.route('/dashboard')
def dashboard():
    if 'username' not in session:
        return redirect(url_for('login'))
    
    # 查询未被选中的票和奖池剩余金额
    try:
        conn = sqlite3.connect('xx.sqlite')
        cursor = conn.cursor()
        cursor.execute('SELECT id, ticket_number FROM tickets WHERE is_selected = 0 ORDER BY id')
        tickets = cursor.fetchall()
        
        # 计算奖池剩余金额（总金额 - 已中奖金额）
        cursor.execute('SELECT COALESCE(SUM(amount), 0) FROM tickets WHERE is_selected = 1 AND amount > 0')
        won_amount = cursor.fetchone()[0] or 0
        
        # 从设置文件获取总金额
        with open('setting.json', 'r', encoding='utf-8') as f:
            settings = json.load(f)
        remaining_prize_pool = settings['total_amount'] - won_amount
        
        conn.close()
    except sqlite3.Error as e:
        print(f"查询票据错误: {e}")
        tickets = []
        remaining_prize_pool = 0
    
    # 分页逻辑
    page = int(request.args.get('page', 1))
    per_page = 9  # 每页显示9张票
    start = (page - 1) * per_page
    end = start + per_page
    tickets_on_page = tickets[start:end]
    
    return render_template('dashboard.html', tickets=tickets_on_page, page=page, remaining_prize_pool=remaining_prize_pool)

@app.route('/scratch_card/<int:ticket_id>')
def scratch_card(ticket_id):
    if 'username' not in session:
        return redirect(url_for('login'))
    
    try:
        # 查询票的详细信息（不立即标记为已使用）
        conn = sqlite3.connect('xx.sqlite')
        cursor = conn.cursor()
        cursor.execute('SELECT ticket_number, amount, is_selected FROM tickets WHERE id = ?', (ticket_id,))
        ticket_info = cursor.fetchone()
        conn.close()
        
        if ticket_info:
            ticket_number, amount, is_selected = ticket_info
            if is_selected:
                return '该票已被使用', 400
            
            # 生成刮刮卡内容
            scratch_data = generate_scratch_card_data(amount)
            return render_template('scratch_card.html', 
                                 ticket_number=ticket_number, 
                                 amount=amount, 
                                 ticket_id=ticket_id,
                                 scratch_data=scratch_data)
        else:
            return '票不存在', 404
    except sqlite3.Error as e:
        print(f"查询票据错误: {e}")
        return '系统错误，请稍后重试', 500

@app.route('/complete_scratch/<int:ticket_id>', methods=['POST'])
def complete_scratch(ticket_id):
    if 'username' not in session:
        return jsonify({'success': False, 'message': '请先登录'}), 403
    
    try:
        # 标记票为已使用
        conn = sqlite3.connect('xx.sqlite')
        cursor = conn.cursor()
        cursor.execute('UPDATE tickets SET is_selected = 1 WHERE id = ? AND is_selected = 0', (ticket_id,))
        affected_rows = cursor.rowcount
        conn.commit()
        conn.close()
        
        if affected_rows > 0:
            return jsonify({'success': True, 'message': '刮奖完成'})
        else:
            return jsonify({'success': False, 'message': '票已被使用或不存在'}), 400
    except sqlite3.Error as e:
        print(f"完成刮奖错误: {e}")
        return jsonify({'success': False, 'message': '系统错误'}), 500

def find_combination_with_n_numbers(nums, m, n):
    m = int(round(m)) if m is not None else 0
    n = int(n)
    # dp[i][j] 表示是否能用 j 个数凑出金额 i
    dp = [[False] * (n + 1) for _ in range(m + 1)]
    dp[0][0] = True

    # prev[i][j] 记录到达金额 i 使用 j 个数时的最后一个数字
    prev = [[None] * (n + 1) for _ in range(m + 1)]

    # 动态规划填充
    for i in range(1, m + 1):
        for j in range(1, n + 1):
            for num in nums:
                if num <= i and dp[i - num][j - 1]:
                    dp[i][j] = True
                    prev[i][j] = num
                    break  # 找到即可停止

    # 如果无法用 n 个数凑出 m
    if not dp[m][n]:
        return False, []

    # 回溯找出组合
    combination = []
    current_amount = m
    current_count = n

    while current_count > 0 and current_amount > 0:
        last_num = prev[current_amount][current_count]
        if last_num is None:
            break
        combination.append(last_num)
        current_amount -= last_num
        current_count -= 1

    return True, combination


def generate_scratch_card_data(total_amount):
    """生成刮刮卡的25个格子数据"""
    import random
    
    # 可选的金额列表
    amount_options = [10, 20, 30, 50, 100,200,500, 1000, 2000, 5000]
    
    # 随机决定中奖位置数量 (0-25)
    winning_positions = random.randint(0, min(25, total_amount // min(amount_options)))
    print(total_amount, "-total_amount :",winning_positions)
    
    # 初始化25个格子
    grid_data = []
    options = [i for i in range(1, 999) if i not in {7, 77, 777}]
    for i in range(25):
        grid_data.append({
            # 'number': random.randint(1, 99),
            'number': random.choice(options),
            'amount': random.choice(amount_options),
            'is_winning': False,
            'multiplier': 1
        })
    
    if winning_positions > 0 and total_amount > 0:
        # 使用动态规划函数寻找精确的货币组合
        while True:
            # 选择中奖位置
            winning_indices = random.sample(range(25), winning_positions)
            print("winning index: ",winning_indices)
            
            # 使用find_combination_with_n_numbers函数
            success, result = find_combination_with_n_numbers(amount_options, total_amount, winning_positions)
            
            if not success:
                # 如果无法找到组合，重新随机winning_positions
                winning_positions = random.randint(0, min(25, total_amount // min(amount_options)))
                print(f"重新生成中奖位置数量: {winning_positions}")
                continue
            else:
                # 根据result分配奖金
                print(f"找到精确组合: {result}")
                
                # 创建金额分配列表
                amounts_to_assign = result
                
                # 随机打乱分配顺序
                random.shuffle(amounts_to_assign)
                
                # 分配给中奖位置
                for i, idx in enumerate(winning_indices):
                    if i < len(amounts_to_assign):
                        amount = amounts_to_assign[i]
                        grid_data[idx]['amount'] = amount
                        grid_data[idx]['is_winning'] = True
                        
                        # 根据位置索引确定倍数和数字
                        grid_data[idx]['multiplier'] = 1
                        grid_data[idx]['number'] = 7
                
                break
    
    return grid_data

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        # 检查用户是否已存在
        existing_user = get_user_from_db(username)
        if existing_user:
            return '用户名已存在'
        
        # 将新用户添加到数据库
        try:
            conn = sqlite3.connect('xx.sqlite')
            cursor = conn.cursor()
            cursor.execute('INSERT INTO users (username, password) VALUES (?, ?)', (username, password))
            conn.commit()
            conn.close()
            return redirect(url_for('login'))
        except sqlite3.Error as e:
            print(f"注册用户错误: {e}")
            return '注册失败，请稍后重试'
    return render_template('register.html')

@app.route('/logout')
def logout():
    session.pop('username', None)
    return redirect(url_for('login'))

@app.route('/admin', methods=['GET', 'POST'])
def admin():
    # 检查是否已经是管理员登录状态
    if 'admin' in session:
        return redirect(url_for('admin_settings'))
    
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
    
    try:
        with open('setting.json', 'r', encoding='utf-8') as f:
            settings = json.load(f)
    except FileNotFoundError:
        settings = {
            'total_tickets': 100,
            'total_amount': 10000,
            'target_winning_tickets': 50,
            'prize_amounts': [10, 20, 30, 50, 100, 200, 500, 1000]
        }
    
    # 查询用户统计和奖池信息
    user_stats = []
    remaining_prize_pool = 0
    remaining_winning_tickets = 0
    winning_tickets = []
    
    try:
        conn = sqlite3.connect('xx.sqlite')
        cursor = conn.cursor()
        
        # 获取所有用户（由于tickets表没有user_id字段，暂时显示基础信息）
        cursor.execute('SELECT username FROM users')
        users = cursor.fetchall()
        
        # 计算总的已刮卡数和总奖金（所有用户共享）
        cursor.execute('SELECT COUNT(*), COALESCE(SUM(amount), 0) FROM tickets WHERE is_selected = 1')
        total_scratched, total_winnings = cursor.fetchone()
        
        # 为每个用户创建统计数据（平均分配或显示总数）
        user_stats = []
        for user in users:
            user_stats.append((user[0], total_scratched or 0, total_winnings or 0))
        
        # 计算奖池剩余金额（总金额 - 已中奖金额）
        cursor.execute('SELECT COALESCE(SUM(amount), 0) FROM tickets WHERE is_selected = 1 AND amount > 0')
        won_amount = cursor.fetchone()[0] or 0
        remaining_prize_pool = settings['total_amount'] - won_amount
        
        # 计算剩余能中奖券数（目标中奖票数 - 已中奖票数）
        cursor.execute('SELECT COUNT(*) FROM tickets WHERE is_selected = 1 AND amount > 0')
        won_tickets = cursor.fetchone()[0] or 0
        remaining_winning_tickets = settings['target_winning_tickets'] - won_tickets
        
        # 获取所有中奖票据信息（包括已刮和未刮的）
        cursor.execute('SELECT ticket_number, amount, is_selected FROM tickets WHERE amount > 0 ORDER BY amount DESC, ticket_number')
        winning_tickets = cursor.fetchall()
        
        conn.close()
    except sqlite3.Error as e:
        print(f"查询统计信息错误: {e}")
    
    if request.method == 'POST':
        # 更新设置
        settings['total_tickets'] = int(request.form['total_tickets'])
        settings['total_amount'] = int(request.form['total_amount'])
        settings['target_winning_tickets'] = int(request.form['target_winning_tickets'])
        
        # 处理多行奖金金额输入
        prize_amounts_text = request.form['prize_amounts']
        prize_amounts = [int(amount.strip()) for amount in prize_amounts_text.split('\n') if amount.strip()]
        settings['prize_amounts'] = prize_amounts
        
        # 保存设置到文件
        with open('setting.json', 'w', encoding='utf-8') as f:
            json.dump(settings, f, indent=4, ensure_ascii=False)
        
        # 重置所有用户的刮卡记录并重新初始化
        try:
            conn = sqlite3.connect('xx.sqlite')
            cursor = conn.cursor()
            
            # 删除所有票据记录
            cursor.execute('DELETE FROM tickets')
            
            # 重新生成奖品频率
            total_tickets = settings['total_tickets']
            total_amount = settings['total_amount']
            prize_amounts = settings['prize_amounts']
            target_winning_tickets = settings['target_winning_tickets']
            prize_frequencies = generate_prize_frequencies(prize_amounts, target_winning_tickets, total_amount)
            
            # 重新插入奖品数据
            cursor.execute('DELETE FROM prizes')
            for i, amount in enumerate(prize_amounts):
                frequency = prize_frequencies[i] if i < len(prize_frequencies) else 0
                cursor.execute('INSERT INTO prizes (amount, frequency) VALUES (?, ?)', (amount, frequency))
            
            # 重新生成票据
            total_tickets = settings['total_tickets']
            target_winning_tickets = settings['target_winning_tickets']
            
            # 生成中奖金额列表
            winning_amounts = []
            for i, amount in enumerate(prize_amounts):
                frequency = prize_frequencies[i] if i < len(prize_frequencies) else 0
                winning_amounts.extend([amount] * frequency)
            
            # 随机选择中奖票据
            import random
            random.shuffle(winning_amounts)
            selected_winning_amounts = winning_amounts[:target_winning_tickets]
            
            # 生成所有票据编号
            all_ticket_numbers = [f"T{i+1:04d}" for i in range(total_tickets)]
            
            # 随机选择中奖票据的编号
            winning_ticket_numbers = random.sample(all_ticket_numbers, target_winning_tickets)
            print(f"中奖票据编号：{winning_ticket_numbers}")    
            
            # 创建票据编号到奖金的映射
            ticket_amounts = {}
            
            # 分配中奖票据
            for i, ticket_number in enumerate(winning_ticket_numbers):
                amount = selected_winning_amounts[i] if i < len(selected_winning_amounts) else 0
                ticket_amounts[ticket_number] = amount
            
            # 分配非中奖票据
            for ticket_number in all_ticket_numbers:
                if ticket_number not in ticket_amounts:
                    ticket_amounts[ticket_number] = 0
            
            # 插入所有票据
            for ticket_number in all_ticket_numbers:
                amount = ticket_amounts[ticket_number]
                cursor.execute('INSERT INTO tickets (ticket_number, amount, is_selected) VALUES (?, ?, 0)', 
                             (ticket_number, amount))
            
            conn.commit()
            conn.close()
            
            print("刮刮卡系统已重置并重新初始化")
        except sqlite3.Error as e:
            print(f"重置系统错误: {e}")
        
        return redirect(url_for('admin_settings'))
    
    return render_template('admin_settings.html', 
                         settings=settings, 
                         user_stats=user_stats,
                         remaining_prize_pool=remaining_prize_pool,
                         remaining_winning_tickets=remaining_winning_tickets,
                         winning_tickets=winning_tickets)

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
    # app.run(debug=True)
    app.run(host='0.0.0.0', port=5000, debug=False)