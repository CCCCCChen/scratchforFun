def find_exact_currency_combination_dp(A, n):
    denominations = [10, 20, 30, 50, 100,200,500, 1000, 2000, 5000]
    denominations.sort(reverse=True)  # 从大到小排序

    # 提前检查无解情况
    if A < n or A > n * denominations[0]:
        return "No exact combination found"

    # 初始化DP表
    dp = [[False] * (n + 1) for _ in range(A + 1)]
    dp[0][0] = True

    # 填充DP表
    for d in denominations:
        for a in range(A, d - 1, -1):
            for m in range(1, n + 1):
                if dp[a - d][m - 1]:
                    dp[a][m] = True

    if not dp[A][n]:
        return "No exact combination found"

    # 回溯找解
    result = []
    remaining_amount = A
    remaining_notes = n
    for d in denominations:
        if remaining_amount == 0 or remaining_notes == 0:
            break
        max_possible = min(remaining_amount // d, remaining_notes)
        for count in range(max_possible, 0, -1):
            if (remaining_amount - count * d >= 0 and
                remaining_notes - count >= 0 and
                dp[remaining_amount - count * d][remaining_notes - count]):
                result.append((d, count))
                remaining_amount -= count * d
                remaining_notes -= count
                break

    return result

def find_combination_with_n_numbers(nums, m, n):
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

# 测试
print(find_exact_currency_combination_dp(500, 3))  # [(50, 1), (20, 1), (5, 1), (1, 1)]

print(find_exact_currency_combination_dp(100, 1))  # [(100, 1)]

found, combination = find_combination_with_n_numbers(nums= [10, 20, 30, 50, 100,200,500, 1000, 2000, 5000], m= 500, n= 3)

if found:
    print(combination)
else:
    print("没有找到精确组合")
