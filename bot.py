from legacy_bot import *

if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True, on_startup=on_startup)
