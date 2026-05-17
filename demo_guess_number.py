import random
import sys

def main():
    print("🎮 猜数字游戏启动")
    print("规则：1-100，你有 7 次机会\n")
    
    target = random.randint(1, 100)
    attempts = 0
    max_attempts = 7
    history = []
    
    while attempts < max_attempts:
        remaining = max_attempts - attempts
        prompt = f"第 {attempts + 1} 次（还剩 {remaining} 次）："
        
        try:
            guess_str = input(prompt)
            guess = int(guess_str)
        except ValueError:
            print("  → 请输入整数")
            continue
        except EOFError:
            print("\n[检测到非交互环境，使用预设测试数据：50, 75, 63]")
            test_inputs = [50, 75, 63]
            if attempts < len(test_inputs):
                guess = test_inputs[attempts]
                print(f"{prompt}{guess}")
            else:
                guess = random.randint(1, 100)
                print(f"{prompt}{guess} (随机)")
        
        attempts += 1
        history.append(guess)
        
        if guess < target:
            print(f"  → 太小了！区间: {guess+1}-100")
        elif guess > target:
            print(f"  → 太大了！区间: 1-{guess-1}")
        else:
            print(f"\n🎯 中了！答案就是 {target}")
            print(f"📊 统计：{attempts} 次猜中，历史记录: {history}")
            return
    
    print(f"\n💀 机会用尽。答案是 {target}")
    print(f"📊 你的猜测历史: {history}")

if __name__ == "__main__":
    main()
