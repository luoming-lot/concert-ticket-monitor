"""独立测试大麦抢票引擎"""
import asyncio, sys, os, traceback

os.chdir(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, '.')

# 清除缓存强制重新加载
for mod in list(sys.modules.keys()):
    if 'app' in mod:
        del sys.modules[mod]

from app.services.damai_bot import DamaiBot, DamaiConfig

config = DamaiConfig(
    target_url='https://www.baidu.com/',
    users=['test_user'],
    max_retries=3,
    if_commit_order=False,
    if_listen=False,
    fast_mode=False,
)

bot = DamaiBot(config, headless=True)  # 用 headless 模式测试，不需要显示器
print('Bot created, running...')

try:
    asyncio.run(bot.run())
except Exception as e:
    print(f'\n=== EXCEPTION ===')
    traceback.print_exc()
finally:
    print('\n=== ALL LOGS ===')
    for l in bot.logs:
        print(f' [{l["level"]:7s}] {l["message"]}')
