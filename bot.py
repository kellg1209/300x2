import logging
import random
import sqlite3
import asyncio
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher, executor, types
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

API_TOKEN = '7912701754:AAGmKlxnA7oXotpSrDxYB4Vv7HW-GS6oMv4'
ADMIN_ID = 6696908898

logging.basicConfig(level=logging.INFO)

bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)

conn = sqlite3.connect('bot.db')
c = conn.cursor()
c.execute('''CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, saldo INTEGER DEFAULT 0, indicado_por INTEGER)''')
c.execute('''CREATE TABLE IF NOT EXISTS apostas (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, numeros TEXT, valor INTEGER, data TEXT)''')
c.execute('''CREATE TABLE IF NOT EXISTS indicacoes (id INTEGER PRIMARY KEY AUTOINCREMENT, indicante INTEGER, indicado INTEGER, bonus_recebido INTEGER DEFAULT 0)''')
conn.commit()

entidade = "10116"
referencia = "957627925"

@dp.message_handler(commands=['start'])
async def start(message: types.Message):
    args = message.get_args()
    user_id = message.from_user.id
    c.execute("INSERT OR IGNORE INTO users (id, saldo) VALUES (?, 0)", (user_id,))
    if args.isdigit():
        indicante = int(args)
        if indicante != user_id:
            c.execute("SELECT * FROM indicacoes WHERE indicado=?", (user_id,))
            if not c.fetchone():
                c.execute("INSERT INTO indicacoes (indicante, indicado) VALUES (?, ?)", (indicante, user_id))
    conn.commit()
    await message.answer("Bem-vindo ao bot de apostas! Use /menu para ver as opções.")

@dp.message_handler(commands=['menu'])
async def menu(message: types.Message):
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add("💰 Depositar", "📤 Sacar", "🎯 Apostar", "📊 Saldo")
    await message.answer("Escolha uma opção:", reply_markup=keyboard)

@dp.message_handler(lambda message: message.text == "💰 Depositar")
async def depositar(message: types.Message):
    await message.answer("Digite o valor que deseja depositar:")
    dp.register_message_handler(receber_valor_deposito, state="esperando_valor_deposito")

depositos_pendentes = {}

async def receber_valor_deposito(message: types.Message):
    try:
        valor = int(message.text)
        if valor < 50:
            await message.answer("Depósito mínimo é 50 Kz.")
            return
        depositos_pendentes[message.from_user.id] = valor
        await message.answer(f"Envie o comprovativo de pagamento\nEntidade: {entidade}\nReferência: {referencia}")
        dp.register_message_handler(receber_comprovativo, content_types=['photo'])
    except:
        await message.answer("Valor inválido. Tente novamente.")

async def receber_comprovativo(message: types.Message):
    user_id = message.from_user.id
    if user_id in depositos_pendentes:
        valor = depositos_pendentes[user_id]
        foto_id = message.photo[-1].file_id
        legenda = f"💰 NOVO DEPÓSITO\nID: {user_id}\nValor: {valor} Kz"
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("✅ Aprovar", callback_data=f"aprovar_{user_id}_{valor}"))
        markup.add(InlineKeyboardButton("❌ Rejeitar", callback_data=f"rejeitar_{user_id}"))
        await bot.send_photo(ADMIN_ID, photo=photo_id, caption=legenda, reply_markup=markup)
        await message.answer("Comprovativo enviado. Aguarde aprovação.")
        del depositos_pendentes[user_id]

@dp.callback_query_handler(lambda call: call.data.startswith("aprovar_"))
async def aprovar_deposito(call: types.CallbackQuery):
    _, user_id, valor = call.data.split("_")
    user_id, valor = int(user_id), int(valor)
    c.execute("UPDATE users SET saldo = saldo + ? WHERE id = ?", (valor, user_id))
    conn.commit()
    await bot.send_message(user_id, f"✅ Seu depósito de {valor} Kz foi aprovado!")

    # Bônus de indicação
    c.execute("SELECT indicante FROM indicacoes WHERE indicado = ? AND bonus_recebido = 0", (user_id,))
    row = c.fetchone()
    if row:
        indicante = row[0]
        c.execute("UPDATE users SET saldo = saldo + 50 WHERE id = ?", (indicante,))
        c.execute("UPDATE indicacoes SET bonus_recebido = 1 WHERE indicado = ?", (user_id,))
        await bot.send_message(indicante, "🎉 Seu indicado fez um depósito! Você ganhou uma aposta grátis de 50 Kz!")
        conn.commit()

@dp.callback_query_handler(lambda call: call.data.startswith("rejeitar_"))
async def rejeitar_deposito(call: types.CallbackQuery):
    _, user_id = call.data.split("_")
    await bot.send_message(int(user_id), "❌ Seu depósito foi rejeitado pelo administrador.")

@dp.message_handler(lambda message: message.text == "📤 Sacar")
async def sacar(message: types.Message):
    await message.answer("Digite o valor que deseja sacar:")
    dp.register_message_handler(receber_valor_saque, state="esperando_valor_saque")

saques_pendentes = {}

async def receber_valor_saque(message: types.Message):
    try:
        valor = int(message.text)
        if valor < 60:
            await message.answer("Saque mínimo é 60 Kz.")
            return
        c.execute("SELECT saldo FROM users WHERE id = ?", (message.from_user.id,))
        saldo = c.fetchone()[0]
        if saldo < valor:
            await message.answer("Saldo insuficiente.")
            return
        saques_pendentes[message.from_user.id] = valor
        await message.answer("Digite a conta para pagamento:")
        dp.register_message_handler(receber_conta_pagamento)
    except:
        await message.answer("Valor inválido. Tente novamente.")

async def receber_conta_pagamento(message: types.Message):
    user_id = message.from_user.id
    valor = saques_pendentes[user_id]
    conta = message.text
    c.execute("UPDATE users SET saldo = saldo - ? WHERE id = ?", (valor, user_id))
    conn.commit()
    await message.answer("Seu saque será processado em até 48h.")
    await bot.send_message(ADMIN_ID, f"📤 Solicitação de Saque\nID: {user_id}\nValor: {valor} Kz\nConta: {conta}")

@dp.message_handler(lambda message: message.text == "📊 Saldo")
async def saldo(message: types.Message):
    c.execute("SELECT saldo FROM users WHERE id = ?", (message.from_user.id,))
    saldo = c.fetchone()[0]
    await message.answer(f"Seu saldo atual é: {saldo} Kz")

@dp.message_handler(lambda message: message.text == "🎯 Apostar")
async def apostar(message: types.Message):
    await message.answer("Digite 3 números de 1 a 90 separados por espaço (ex: 5 22 87):")
    dp.register_message_handler(receber_aposta)

async def receber_aposta(message: types.Message):
    try:
        numeros = list(map(int, message.text.strip().split()))
        if len(numeros) != 3 or not all(1 <= n <= 90 for n in numeros):
            await message.answer("Você deve enviar exatamente 3 números entre 1 e 90.")
            return
        c.execute("SELECT saldo FROM users WHERE id = ?", (message.from_user.id,))
        saldo = c.fetchone()[0]
        if saldo < 25:
            await message.answer("Saldo insuficiente. Aposta mínima é 25 Kz.")
            return
        c.execute("UPDATE users SET saldo = saldo - 25 WHERE id = ?", (message.from_user.id,))
        c.execute("INSERT INTO apostas (user_id, numeros, valor, data) VALUES (?, ?, ?, ?)",
                  (message.from_user.id, " ".join(map(str, numeros)), 25, datetime.now().isoformat()))
        conn.commit()
        await message.answer("Aposta registrada com sucesso!")
    except:
        await message.answer("Formato inválido. Tente novamente.")

async def sorteio():
    while True:
        agora = datetime.now()
        if agora.hour in [12, 16, 20] and agora.minute == 0:
            await processar_sorteio()
            await asyncio.sleep(60)
        await asyncio.sleep(10)

async def processar_sorteio():
    hoje = datetime.now().date()
    c.execute("SELECT * FROM apostas WHERE data LIKE ?", (f"{hoje}%",))
    apostas = c.fetchall()
    if not apostas:
        return
    numeros_sorteados = random.sample(range(1, 91), 20)
    vencedores = []
    for aposta in apostas:
        numeros_apostados = list(map(int, aposta[2].split()))
        if all(num in numeros_sorteados for num in numeros_apostados):
            vencedores.append(aposta[1])
    for vencedor in set(vencedores):
        c.execute("UPDATE users SET saldo = saldo + ? WHERE id = ?", (25 * 300, vencedor))
        await bot.send_message(vencedor, "🎉 Parabéns! Você ganhou a rodada!")
    conn.commit()
    for aposta in apostas:
        c.execute("DELETE FROM apostas WHERE id = ?", (aposta[0],))
    conn.commit()

if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.create_task(sorteio())
    executor.start_polling(dp, skip_updates=True)
