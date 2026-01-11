import os
import logging
import sqlite3
import calendar
from datetime import datetime, date

from aiogram import Bot, Dispatcher, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.types import (
    ReplyKeyboardMarkup,
    KeyboardButton,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    CallbackQuery,
)
from aiogram.utils import executor

# ===================== НАСТРОЙКИ =====================

# Токен и ID главного админа берем из переменных окружения
API_TOKEN = os.getenv("BOT_TOKEN", "8535476214:AAGXYR7yLd_gK4mbzGA1EpagKgQMLHVvmdY").strip()
if not API_TOKEN:
    raise RuntimeError("Не задана переменная окружения BOT_TOKEN")

SUPER_ADMIN_ID = int(os.getenv("SUPER_ADMIN_ID", "5240248802"))
if SUPER_ADMIN_ID == 0:
    raise RuntimeError("Не задана переменная окружения SUPER_ADMIN_ID")

logging.basicConfig(level=logging.INFO)

bot = Bot(token=API_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)

# Путь к базе данных рядом с bot.py
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "bot.db")


# ===================== РАБОТА С БАЗОЙ ДАННЫХ =====================

def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_conn()
    cur = conn.cursor()

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS applications(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            username TEXT,
            full_name TEXT,
            created_at TEXT,
            place_birth TEXT,
            email TEXT,
            passport_number TEXT,
            home_address TEXT,
            phone TEXT,
            father_name TEXT,
            father_birth_place TEXT,
            mother_name TEXT,
            mother_birth_place TEXT,
            marital_status TEXT,
            spouse_name TEXT,
            spouse_birth_place TEXT,
            work_place TEXT,
            work_address TEXT,
            airport TEXT,
            visa_term TEXT,
            arrival_date TEXT,
            contact_name TEXT,
            contact_phone TEXT,
            contact_address TEXT,
            hotel_booked TEXT,
            hotel_details TEXT,
            five_year_visa TEXT,
            visa_refusal TEXT,
            visa_refusal_details TEXT,
            trips_last_5y TEXT,
            last_visa_details TEXT,
            outside_india TEXT,
            overstay TEXT,
            status TEXT,
            admin_comment TEXT,
            admin_id INTEGER
        )
        """
    )

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS admins(
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            is_superadmin INTEGER DEFAULT 0
        )
        """
    )

    # гарантируем, что главный админ есть
    cur.execute(
        "INSERT OR IGNORE INTO admins (user_id, username, is_superadmin) VALUES (?, ?, 1)",
        (SUPER_ADMIN_ID, None),
    )

    conn.commit()
    conn.close()


def is_admin(user_id: int) -> bool:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT 1 FROM admins WHERE user_id=?", (user_id,))
    row = cur.fetchone()
    conn.close()
    return row is not None


def is_superadmin(user_id: int) -> bool:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT is_superadmin FROM admins WHERE user_id=?", (user_id,))
    row = cur.fetchone()
    conn.close()
    return bool(row and row["is_superadmin"] == 1)


def get_admins():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM admins")
    rows = cur.fetchall()
    conn.close()
    return rows


def upsert_admin(user_id: int, username: str, is_super: bool = False):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO admins (user_id, username, is_superadmin)
        VALUES (?, ?, ?)
        ON CONFLICT(user_id) DO UPDATE SET
            username=excluded.username,
            is_superadmin=excluded.is_superadmin
        """,
        (user_id, username, 1 if is_super else 0),
    )
    conn.commit()
    conn.close()


def save_application(user_id: int, username: str, data: dict) -> int:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO applications (
            user_id, username, full_name, created_at,
            place_birth, email, passport_number,
            home_address, phone,
            father_name, father_birth_place,
            mother_name, mother_birth_place,
            marital_status,
            spouse_name, spouse_birth_place,
            work_place, work_address,
            airport, visa_term, arrival_date,
            contact_name, contact_phone, contact_address,
            hotel_booked, hotel_details,
            five_year_visa,
            visa_refusal, visa_refusal_details,
            trips_last_5y, last_visa_details,
            outside_india, overstay,
            status, admin_comment, admin_id
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            user_id,
            username,
            data.get("full_name", ""),
            datetime.utcnow().isoformat(timespec="seconds"),
            data.get("place_birth", ""),
            data.get("email", ""),
            data.get("passport_number", ""),
            data.get("home_address", ""),
            data.get("phone", ""),
            data.get("father_name", ""),
            data.get("father_birth_place", ""),
            data.get("mother_name", ""),
            data.get("mother_birth_place", ""),
            data.get("marital_status", ""),
            data.get("spouse_name", ""),
            data.get("spouse_birth_place", ""),
            data.get("work_place", ""),
            data.get("work_address", ""),
            data.get("airport", ""),
            data.get("visa_term", ""),
            data.get("arrival_date", ""),
            data.get("contact_name", ""),
            data.get("contact_phone", ""),
            data.get("contact_address", ""),
            data.get("hotel_booked", ""),
            data.get("hotel_details", ""),
            data.get("five_year_visa", ""),
            data.get("visa_refusal", ""),
            data.get("visa_refusal_details", ""),
            data.get("trips_last_5y", ""),
            data.get("last_visa_details", ""),
            data.get("outside_india", ""),
            data.get("overstay", ""),
            "в ожидании",
            "",
            None,
        ),
    )
    app_id = cur.lastrowid
    conn.commit()
    conn.close()
    return app_id


def get_application(app_id: int):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM applications WHERE id=?", (app_id,))
    row = cur.fetchone()
    conn.close()
    return row


def update_application_status(app_id: int, status: str, admin_id: int, comment: str = ""):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "UPDATE applications SET status=?, admin_id=?, admin_comment=? WHERE id=?",
        (status, admin_id, comment, app_id),
    )
    conn.commit()
    conn.close()


def list_applications(only_pending: bool = False, limit: int = 20):
    conn = get_conn()
    cur = conn.cursor()
    if only_pending:
        cur.execute(
            """
            SELECT id, created_at, username, status
            FROM applications
            WHERE status='в ожидании'
            ORDER BY datetime(created_at) DESC
            LIMIT ?
            """,
            (limit,),
        )
    else:
        cur.execute(
            """
            SELECT id, created_at, username, status
            FROM applications
            ORDER BY datetime(created_at) DESC
            LIMIT ?
            """,
            (limit,),
        )
    rows = cur.fetchall()
    conn.close()
    return rows


# ===================== СОСТОЯНИЯ (FSM) =====================

class Form(StatesGroup):
    full_name = State()
    place_birth = State()
    email = State()
    passport_number = State()
    home_address = State()
    phone = State()
    father_name = State()
    father_birth_place = State()
    mother_name = State()
    mother_birth_place = State()
    marital_status = State()
    spouse_name = State()
    spouse_birth_place = State()
    work_place = State()
    work_address = State()
    airport = State()
    visa_term = State()
    arrival_date = State()
    contact_name = State()
    contact_phone = State()
    contact_address = State()
    hotel_booked = State()
    hotel_details = State()
    five_year_visa = State()
    five_year_visa_details = State()
    visa_refusal = State()
    visa_refusal_details = State()
    trips_last_5y = State()
    last_visa_details = State()
    outside_india = State()
    overstay = State()
    confirm = State()


class AdminDialog(StatesGroup):
    waiting_for_text = State()


# ===================== КЛАВИАТУРЫ =====================

user_main_kb = ReplyKeyboardMarkup(resize_keyboard=True)
user_main_kb.add(KeyboardButton("Заполнить анкету"))

admin_main_kb = ReplyKeyboardMarkup(resize_keyboard=True)
admin_main_kb.add(KeyboardButton("Заполнить анкету"), KeyboardButton("Админ-панель"))


def airport_kb() -> InlineKeyboardMarkup:
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(
        InlineKeyboardButton("Даболим", callback_data="airport:Dabolim"),
        InlineKeyboardButton("Мора", callback_data="airport:Mopa"),
    )
    return kb


def visa_term_kb() -> InlineKeyboardMarkup:
    kb = InlineKeyboardMarkup(row_width=3)
    kb.add(
        InlineKeyboardButton("30 дней", callback_data="visaterm:30d"),
        InlineKeyboardButton("1 год", callback_data="visaterm:1y"),
        InlineKeyboardButton("5 лет", callback_data="visaterm:5y"),
    )
    return kb


def yes_no_kb(prefix: str) -> InlineKeyboardMarkup:
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(
        InlineKeyboardButton("Да", callback_data=f"{prefix}:yes"),
        InlineKeyboardButton("Нет", callback_data=f"{prefix}:no"),
    )
    return kb


def admin_panel_kb() -> InlineKeyboardMarkup:
    kb = InlineKeyboardMarkup(row_width=1)
    kb.add(
        InlineKeyboardButton("Новые заявки", callback_data="admin:new"),
        InlineKeyboardButton("Все заявки", callback_data="admin:all"),
        InlineKeyboardButton("Список админов", callback_data="admin:admins"),
    )
    return kb


def admin_application_kb(app_id: int) -> InlineKeyboardMarkup:
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(
        InlineKeyboardButton("Одобрить", callback_data=f"approve:{app_id}"),
        InlineKeyboardButton("Отклонить", callback_data=f"reject:{app_id}"),
    )
    kb.add(
        InlineKeyboardButton("Написать пользователю", callback_data=f"msguser:{app_id}")
    )
    kb.add(
        InlineKeyboardButton("Сделать админом", callback_data=f"makeadmin:{app_id}")
    )
    return kb


def confirm_kb() -> InlineKeyboardMarkup:
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(
        InlineKeyboardButton("Отправить", callback_data="confirm:send"),
        InlineKeyboardButton("Редактировать анкету", callback_data="confirm:edit"),
    )
    return kb


def create_calendar() -> InlineKeyboardMarkup:
    today = date.today()
    year, month = today.year, today.month
    cal = calendar.monthcalendar(year, month)

    kb = InlineKeyboardMarkup(row_width=7)

    month_name = calendar.month_name[month]
    kb.row(InlineKeyboardButton(f"{month_name} {year}", callback_data="ignore"))

    week_days = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]
    kb.row(*[InlineKeyboardButton(d, callback_data="ignore") for d in week_days])

    for week in cal:
        row = []
        for day in week:
            if day == 0:
                row.append(InlineKeyboardButton(" ", callback_data="ignore"))
            else:
                date_str = f"{year:04d}-{month:02d}-{day:02d}"
                row.append(
                    InlineKeyboardButton(str(day), callback_data=f"cal:{date_str}")
                )
        kb.row(*row)

    return kb


EDIT_FIELDS = [
    ("full_name", "ФИО"),
    ("place_birth", "1. Место рождения"),
    ("email", "2. Электронная почта"),
    ("passport_number", "3. Номер паспорта"),
    ("home_address", "4. Домашний адрес"),
    ("phone", "5. Телефон"),
    ("father_name", "6. ФИО отца"),
    ("father_birth_place", "7. Место рождения отца"),
    ("mother_name", "8. ФИО матери"),
    ("mother_birth_place", "8*. Место рождения матери"),
    ("marital_status", "9. Семейное положение"),
    ("spouse_name", "10. ФИО супруга(и)"),
    ("spouse_birth_place", "11. Место рождения супруга(и)"),
    ("work_place", "12. Место работы"),
    ("work_address", "13. Адрес работы"),
    ("airport", "14. Аэропорт прибытия"),
    ("visa_term", "15. Срок визы"),
    ("arrival_date", "16. Дата прибытия"),
    ("contact_name", "17. Контактное лицо"),
    ("contact_phone", "18. Телефон контакта"),
    ("contact_address", "19. Адрес контакта"),
    ("hotel_booked", "20. Отель"),
    ("five_year_visa", "21. 5-летняя виза"),
    ("visa_refusal", "22. Отказы по визе"),
    ("trips_last_5y", "23. Поездки за 5 лет"),
    ("last_visa_details", "24. Детали последней визы"),
    ("outside_india", "25. Находились вне Индии"),
    ("overstay", "26. Превышение сроков / exit permit"),
]


def edit_menu_kb() -> InlineKeyboardMarkup:
    kb = InlineKeyboardMarkup(row_width=2)
    for field, title in EDIT_FIELDS:
        kb.insert(InlineKeyboardButton(title, callback_data=f"edit:{field}"))
    return kb


# ===================== ВСПОМОГАТЕЛЬНОЕ =====================

def format_application_text(app: sqlite3.Row) -> str:
    uname = f"@{app['username']}" if app["username"] else "без username"
    status = app["status"] or "в ожидании"
    lines = [
        f"Заявка №{app['id']} (статус: {status})",
        f"Создана: {app['created_at']}",
        "",
        f"Пользователь: {uname} (ID {app['user_id']})",
        f"ФИО: {app['full_name']}",
        "",
        f"1. Место рождения: {app['place_birth']}",
        f"2. Электронная почта: {app['email']}",
        f"3. Номер национального паспорта: {app['passport_number']}",
        f"4. Домашний адрес: {app['home_address']}",
        f"5. Номер телефона: {app['phone']}",
        f"6. ФИО отца: {app['father_name']}",
        f"7. Место рождения отца: {app['father_birth_place']}",
        f"8. ФИО матери: {app['mother_name']}",
        f"   Место рождения матери: {app['mother_birth_place']}",
        f"9. Семейное положение: {app['marital_status']}",
        f"10. ФИО супруга(и): {app['spouse_name']}",
        f"11. Место рождения супруга(и): {app['spouse_birth_place']}",
        f"12. Место работы: {app['work_place']}",
        f"13. Адрес места работы: {app['work_address']}",
        f"14. Аэропорт/порт прибытия: {app['airport']}",
        f"15. Срок визы: {app['visa_term']}",
        f"16. Дата прибытия: {app['arrival_date']}",
        f"17. ФИО контактного лица в России: {app['contact_name']}",
        f"18. Телефон контактного лица: {app['contact_phone']}",
        f"19. Адрес контактного лица: {app['contact_address']}",
        f"20. Отель забронирован: {app['hotel_booked']}",
        f"    Детали отеля: {app['hotel_details']}",
        f"21. 5-летние визы в Индию и срок действия: {app['five_year_visa']}",
        f"22. Отказы по визе в Индию: {app['visa_refusal']}",
        f"    Детали отказов: {app['visa_refusal_details']}",
        f"23. Поездки в Индию за последние 5 лет: {app['trips_last_5y']}",
        f"24. Номер последней визы, дата выдачи, адрес проживания: {app['last_visa_details']}",
        f"25. Сейчас вы за пределами Индии: {app['outside_india']}",
        f"26. Exit permit / превышения сроков пребывания: {app['overstay']}",
    ]
    return "\n".join(lines)


def format_preview_from_data(user: types.User, data: dict) -> str:
    uname = f"@{user.username}" if user.username else "без username"
    lines = [
        f"Ваш username: {uname}",
        f"ФИО: {data.get('full_name', '')}",
        "",
        f"1. Место рождения: {data.get('place_birth', '')}",
        f"2. Электронная почта: {data.get('email', '')}",
        f"3. Номер национального паспорта: {data.get('passport_number', '')}",
        f"4. Домашний адрес: {data.get('home_address', '')}",
        f"5. Номер телефона: {data.get('phone', '')}",
        f"6. ФИО отца: {data.get('father_name', '')}",
        f"7. Место рождения отца: {data.get('father_birth_place', '')}",
        f"8. ФИО матери: {data.get('mother_name', '')}",
        f"   Место рождения матери: {data.get('mother_birth_place', '')}",
        f"9. Семейное положение: {data.get('marital_status', '')}",
        f"10. ФИО супруга(и): {data.get('spouse_name', '')}",
        f"11. Место рождения супруга(и): {data.get('spouse_birth_place', '')}",
        f"12. Место работы: {data.get('work_place', '')}",
        f"13. Адрес места работы: {data.get('work_address', '')}",
        f"14. Аэропорт/порт прибытия: {data.get('airport', '')}",
        f"15. Срок визы: {data.get('visa_term', '')}",
        f"16. Дата прибытия: {data.get('arrival_date', '')}",
        f"17. ФИО контактного лица в России: {data.get('contact_name', '')}",
        f"18. Телефон контактного лица: {data.get('contact_phone', '')}",
        f"19. Адрес контактного лица: {data.get('contact_address', '')}",
        f"20. Отель забронирован: {data.get('hotel_booked', '')}",
        f"    Детали отеля: {data.get('hotel_details', '')}",
        f"21. 5-летние визы в Индию и срок действия: {data.get('five_year_visa', '')}",
        f"22. Отказы по визе в Индию: {data.get('visa_refusal', '')}",
        f"    Детали отказов: {data.get('visa_refusal_details', '')}",
        f"23. Поездки в Индию за последние 5 лет: {data.get('trips_last_5y', '')}",
        f"24. Номер последней визы, дата выдачи, адрес проживания: {data.get('last_visa_details', '')}",
        f"25. Сейчас вы за пределами Индии: {data.get('outside_india', '')}",
        f"26. Exit permit / превышения сроков пребывания: {data.get('overstay', '')}",
    ]
    return "\n".join(lines)


async def show_preview(message: types.Message, state: FSMContext):
    data = await state.get_data()
    text = format_preview_from_data(message.from_user, data)
    await message.answer(
        "Проверьте, пожалуйста, вашу анкету:\n\n"
        + text
        + "\n\nЕсли всё верно, нажмите «Отправить».\n"
          "Если нужно что-то поменять — «Редактировать анкету».",
        reply_markup=confirm_kb(),
    )


async def notify_admins_about_application(app_id: int):
    app = get_application(app_id)
    if not app:
        return
    text = format_application_text(app)
    admins = get_admins()
    for adm in admins:
        try:
            await bot.send_message(
                adm["user_id"],
                text,
                reply_markup=admin_application_kb(app_id),
            )
        except Exception as e:
            logging.warning(f"Не удалось отправить заявку админу {adm['user_id']}: {e}")


# ===================== ХЕНДЛЕРЫ ПОЛЬЗОВАТЕЛЯ =====================

@dp.message_handler(commands=["start"])
async def cmd_start(message: types.Message, state: FSMContext):
    if message.from_user.id == SUPER_ADMIN_ID:
        upsert_admin(
            message.from_user.id,
            message.from_user.username or "",
            is_super=True,
        )

    kb = admin_main_kb if is_admin(message.from_user.id) else user_main_kb

    await state.finish()
    await message.answer(
        "Здравствуйте!\n\n"
        "Этот бот собирает анкету для оформления визы в Индию.\n"
        "Нажмите кнопку «Заполнить анкету», чтобы начать.",
        reply_markup=kb,
    )


@dp.message_handler(lambda m: m.text == "Заполнить анкету")
async def start_form(message: types.Message, state: FSMContext):
    await state.finish()
    await Form.full_name.set()
    await message.answer("Ваше ФИО (Фамилия Имя Отчество):")


# ---------- ВОПРОСЫ ----------

@dp.message_handler(state=Form.full_name)
async def form_full_name(message: types.Message, state: FSMContext):
    await state.update_data(full_name=message.text.strip())
    data = await state.get_data()
    if data.get("editing"):
        await Form.confirm.set()
        await show_preview(message, state)
    else:
        await Form.place_birth.set()
        await message.answer("1. Место вашего рождения (город/село/область):")


@dp.message_handler(state=Form.place_birth)
async def form_place_birth(message: types.Message, state: FSMContext):
    await state.update_data(place_birth=message.text.strip())
    data = await state.get_data()
    if data.get("editing"):
        await Form.confirm.set()
        await show_preview(message, state)
    else:
        await Form.email.set()
        await message.answer("2. Ваша электронная почта:")


@dp.message_handler(state=Form.email)
async def form_email(message: types.Message, state: FSMContext):
    await state.update_data(email=message.text.strip())
    data = await state.get_data()
    if data.get("editing"):
        await Form.confirm.set()
        await show_preview(message, state)
    else:
        await Form.passport_number.set()
        await message.answer("3. Номер национального паспорта:")


@dp.message_handler(state=Form.passport_number)
async def form_passport_number(message: types.Message, state: FSMContext):
    await state.update_data(passport_number=message.text.strip())
    data = await state.get_data()
    if data.get("editing"):
        await Form.confirm.set()
        await show_preview(message, state)
    else:
        await Form.home_address.set()
        await message.answer(
            "4. Домашний адрес (Город, улица, номер дома, квартира, индекс):"
        )


@dp.message_handler(state=Form.home_address)
async def form_home_address(message: types.Message, state: FSMContext):
    await state.update_data(home_address=message.text.strip())
    data = await state.get_data()
    if data.get("editing"):
        await Form.confirm.set()
        await show_preview(message, state)
    else:
        await Form.phone.set()
        await message.answer("5. Ваш номер телефона:")


@dp.message_handler(state=Form.phone)
async def form_phone(message: types.Message, state: FSMContext):
    await state.update_data(phone=message.text.strip())
    data = await state.get_data()
    if data.get("editing"):
        await Form.confirm.set()
        await show_preview(message, state)
    else:
        await Form.father_name.set()
        await message.answer("6. Фамилия, имя отца (даже если нет в живых):")


@dp.message_handler(state=Form.father_name)
async def form_father_name(message: types.Message, state: FSMContext):
    await state.update_data(father_name=message.text.strip())
    data = await state.get_data()
    if data.get("editing"):
        await Form.confirm.set()
        await show_preview(message, state)
    else:
        await Form.father_birth_place.set()
        await message.answer("7. Место рождения отца:")


@dp.message_handler(state=Form.father_birth_place)
async def form_father_birth_place(message: types.Message, state: FSMContext):
    await state.update_data(father_birth_place=message.text.strip())
    data = await state.get_data()
    if data.get("editing"):
        await Form.confirm.set()
        await show_preview(message, state)
    else:
        await Form.mother_name.set()
        await message.answer("8. Фамилия, имя матери (даже если нет в живых):")


@dp.message_handler(state=Form.mother_name)
async def form_mother_name(message: types.Message, state: FSMContext):
    await state.update_data(mother_name=message.text.strip())
    data = await state.get_data()
    if data.get("editing"):
        await Form.confirm.set()
        await show_preview(message, state)
    else:
        await Form.mother_birth_place.set()
        await message.answer("8. Место рождения матери:")


@dp.message_handler(state=Form.mother_birth_place)
async def form_mother_birth_place(message: types.Message, state: FSMContext):
    await state.update_data(mother_birth_place=message.text.strip())
    data = await state.get_data()
    if data.get("editing"):
        await Form.confirm.set()
        await show_preview(message, state)
    else:
        await Form.marital_status.set()
        await message.answer("9. Ваше семейное положение:")


@dp.message_handler(state=Form.marital_status)
async def form_marital_status(message: types.Message, state: FSMContext):
    await state.update_data(marital_status=message.text.strip())
    data = await state.get_data()
    if data.get("editing"):
        await Form.confirm.set()
        await show_preview(message, state)
    else:
        await Form.spouse_name.set()
        await message.answer(
            "10. Если вы в браке, укажите фамилию и имя вашего супруга(и). "
            "Если не в браке, напишите «нет»:"
        )


@dp.message_handler(state=Form.spouse_name)
async def form_spouse_name(message: types.Message, state: FSMContext):
    await state.update_data(spouse_name=message.text.strip())
    data = await state.get_data()
    if data.get("editing"):
        await Form.confirm.set()
        await show_preview(message, state)
    else:
        await Form.spouse_birth_place.set()
        await message.answer(
            "11. Место рождения вашего супруга(и). "
            "Если не в браке, напишите «нет»:"
        )


@dp.message_handler(state=Form.spouse_birth_place)
async def form_spouse_birth_place(message: types.Message, state: FSMContext):
    await state.update_data(spouse_birth_place=message.text.strip())
    data = await state.get_data()
    if data.get("editing"):
        await Form.confirm.set()
        await show_preview(message, state)
    else:
        await Form.work_place.set()
        await message.answer(
            "12. Название вашего места работы "
            "(если не работаете, напишите «безработный(ая)»):"
        )


@dp.message_handler(state=Form.work_place)
async def form_work_place(message: types.Message, state: FSMContext):
    await state.update_data(work_place=message.text.strip())
    data = await state.get_data()
    if data.get("editing"):
        await Form.confirm.set()
        await show_preview(message, state)
    else:
        await Form.work_address.set()
        await message.answer(
            "13. Адрес вашего места работы "
            "(если не работаете, напишите «безработный(ая)»):"
        )


@dp.message_handler(state=Form.work_address)
async def form_work_address(message: types.Message, state: FSMContext):
    await state.update_data(work_address=message.text.strip())
    data = await state.get_data()
    if data.get("editing"):
        await Form.confirm.set()
        await show_preview(message, state)
    else:
        await Form.airport.set()
        await message.answer(
            "14. Аэропорт или порт планируемого прибытия в Индию:",
            reply_markup=airport_kb(),
        )


@dp.callback_query_handler(lambda c: c.data.startswith("airport:"), state=Form.airport)
async def form_airport(callback_query: CallbackQuery, state: FSMContext):
    code = callback_query.data.split(":", 1)[1]
    value = "Даболим" if code == "Dabolim" else "Мора"
    await state.update_data(airport=value)
    data = await state.get_data()
    await callback_query.answer(f"Вы выбрали: {value}")

    if data.get("editing"):
        await Form.confirm.set()
        await show_preview(callback_query.message, state)
    else:
        await Form.visa_term.set()
        await callback_query.message.answer(
            "15. На какой срок нужна виза:", reply_markup=visa_term_kb()
        )


@dp.callback_query_handler(lambda c: c.data.startswith("visaterm:"), state=Form.visa_term)
async def form_visa_term(callback_query: CallbackQuery, state: FSMContext):
    code = callback_query.data.split(":", 1)[1]
    mapping = {"30d": "30 дней", "1y": "1 год", "5y": "5 лет"}
    value = mapping.get(code, "")
    await state.update_data(visa_term=value)
    data = await state.get_data()
    await callback_query.answer(f"Вы выбрали: {value}")

    if data.get("editing"):
        await Form.confirm.set()
        await show_preview(callback_query.message, state)
    else:
        await Form.arrival_date.set()
        await callback_query.message.answer(
            "16. Дата планируемого прибытия в Индию (выберите дату на календаре):",
            reply_markup=create_calendar(),
        )


@dp.callback_query_handler(lambda c: c.data == "ignore", state=Form.arrival_date)
async def ignore_calendar(callback_query: CallbackQuery, state: FSMContext):
    await callback_query.answer()


@dp.callback_query_handler(lambda c: c.data.startswith("cal:"), state=Form.arrival_date)
async def form_arrival_date(callback_query: CallbackQuery, state: FSMContext):
    date_str = callback_query.data.split(":", 1)[1]
    await state.update_data(arrival_date=date_str)
    data = await state.get_data()
    await callback_query.answer(f"Дата выбрана: {date_str}")

    if data.get("editing"):
        await Form.confirm.set()
        await show_preview(callback_query.message, state)
    else:
        await Form.contact_name.set()
        await callback_query.message.answer("17. Фамилия и имя контактного лица в России:")


@dp.message_handler(state=Form.contact_name)
async def form_contact_name(message: types.Message, state: FSMContext):
    await state.update_data(contact_name=message.text.strip())
    data = await state.get_data()
    if data.get("editing"):
        await Form.confirm.set()
        await show_preview(message, state)
    else:
        await Form.contact_phone.set()
        await message.answer("18. Телефон контактного лица в России:")


@dp.message_handler(state=Form.contact_phone)
async def form_contact_phone(message: types.Message, state: FSMContext):
    await state.update_data(contact_phone=message.text.strip())
    data = await state.get_data()
    if data.get("editing"):
        await Form.confirm.set()
        await show_preview(message, state)
    else:
        await Form.contact_address.set()
        await message.answer("19. Адрес контактного лица в России:")


@dp.message_handler(state=Form.contact_address)
async def form_contact_address(message: types.Message, state: FSMContext):
    await state.update_data(contact_address=message.text.strip())
    data = await state.get_data()
    if data.get("editing"):
        await Form.confirm.set()
        await show_preview(message, state)
    else:
        await Form.hotel_booked.set()
        await message.answer(
            "20. Если забронирован отель, выберите «Да». Если нет — «Нет»:",
            reply_markup=yes_no_kb("hotel"),
        )


@dp.callback_query_handler(lambda c: c.data.startswith("hotel:"), state=Form.hotel_booked)
async def form_hotel(callback_query: CallbackQuery, state: FSMContext):
    ans = callback_query.data.split(":", 1)[1]
    value = "Да" if ans == "yes" else "Нет"
    await state.update_data(hotel_booked=value)
    data = await state.get_data()
    await callback_query.answer(value)

    if value == "Да":
        await Form.hotel_details.set()
        await callback_query.message.answer("Укажите название отеля и его адрес:")
    else:
        if data.get("editing"):
            await Form.confirm.set()
            await show_preview(callback_query.message, state)
        else:
            await Form.five_year_visa.set()
            await callback_query.message.answer(
                "21. Были ли у вас 5-летние визы в Индию?",
                reply_markup=yes_no_kb("fivevisa"),
            )


@dp.message_handler(state=Form.hotel_details)
async def form_hotel_details(message: types.Message, state: FSMContext):
    await state.update_data(hotel_details=message.text.strip())
    data = await state.get_data()
    if data.get("editing"):
        await Form.confirm.set()
        await show_preview(message, state)
    else:
        await Form.five_year_visa.set()
        await message.answer(
            "21. Были ли у вас 5-летние визы в Индию?",
            reply_markup=yes_no_kb("fivevisa"),
        )


@dp.callback_query_handler(lambda c: c.data.startswith("fivevisa:"), state=Form.five_year_visa)
async def form_five_year_visa_cb(callback_query: CallbackQuery, state: FSMContext):
    ans = callback_query.data.split(":", 1)[1]
    await callback_query.answer()
    data = await state.get_data()
    editing = data.get("editing")

    if ans == "no":
        await state.update_data(five_year_visa="Нет")
        if editing:
            await Form.confirm.set()
            await show_preview(callback_query.message, state)
        else:
            await Form.visa_refusal.set()
            await callback_query.message.answer(
                "22. Были ли у вас отказы по визе в Индию:",
                reply_markup=yes_no_kb("vref"),
            )
    else:
        await state.update_data(five_year_visa="Да")
        await Form.five_year_visa_details.set()
        await callback_query.message.answer(
            "Укажите срок, до которого действовала 5-летняя виза, "
            "и любую дополнительную информацию:"
        )


@dp.message_handler(state=Form.five_year_visa_details)
async def form_five_year_visa_details(message: types.Message, state: FSMContext):
    details = message.text.strip()
    data = await state.get_data()
    editing = data.get("editing")

    base = "Да"
    if details:
        base += f", детали: {details}"
    await state.update_data(five_year_visa=base)

    if editing:
        await Form.confirm.set()
        await show_preview(message, state)
    else:
        await Form.visa_refusal.set()
        await message.answer(
            "22. Были ли у вас отказы по визе в Индию:",
            reply_markup=yes_no_kb("vref"),
        )


@dp.callback_query_handler(lambda c: c.data.startswith("vref:"), state=Form.visa_refusal)
async def form_visa_refusal(callback_query: CallbackQuery, state: FSMContext):
    ans = callback_query.data.split(":", 1)[1]
    value = "Да" if ans == "yes" else "Нет"
    await state.update_data(visa_refusal=value)
    data = await state.get_data()
    editing = data.get("editing")
    await callback_query.answer(value)

    if value == "Да":
        await Form.visa_refusal_details.set()
        await callback_query.message.answer(
            "Опишите, по какой причине были отказы по визе в Индию:"
        )
    else:
        if editing:
            await Form.confirm.set()
            await show_preview(callback_query.message, state)
        else:
            await Form.trips_last_5y.set()
            await callback_query.message.answer(
                "23. Если были поездки в Индию за последние 5 лет, "
                "укажите даты и цель поездок:"
            )


@dp.message_handler(state=Form.visa_refusal_details)
async def form_visa_refusal_details(message: types.Message, state: FSMContext):
    await state.update_data(visa_refusal_details=message.text.strip())
    data = await state.get_data()
    if data.get("editing"):
        await Form.confirm.set()
        await show_preview(message, state)
    else:
        await Form.trips_last_5y.set()
        await message.answer(
            "23. Если были поездки в Индию за последние 5 лет, "
            "укажите даты и цель поездок:"
        )


@dp.message_handler(state=Form.trips_last_5y)
async def form_trips_last_5y(message: types.Message, state: FSMContext):
    await state.update_data(trips_last_5y=message.text.strip())
    data = await state.get_data()
    if data.get("editing"):
        await Form.confirm.set()
        await show_preview(message, state)
    else:
        await Form.last_visa_details.set()
        await message.answer(
            "24. Номер последней визы, дата выдачи последней визы, "
            "адрес проживания по последней поездке:"
        )


@dp.message_handler(state=Form.last_visa_details)
async def form_last_visa_details(message: types.Message, state: FSMContext):
    await state.update_data(last_visa_details=message.text.strip())
    data = await state.get_data()
    if data.get("editing"):
        await Form.confirm.set()
        await show_preview(message, state)
    else:
        await Form.outside_india.set()
        await message.answer(
            "25. В момент оформления вы находитесь за пределами Индии?",
            reply_markup=yes_no_kb("outindia"),
        )


@dp.callback_query_handler(lambda c: c.data.startswith("outindia:"), state=Form.outside_india)
async def form_outside_india(callback_query: CallbackQuery, state: FSMContext):
    ans = callback_query.data.split(":", 1)[1]
    value = "Да" if ans == "yes" else "Нет"
    await state.update_data(outside_india=value)
    data = await state.get_data()
    editing = data.get("editing")
    await callback_query.answer(value)

    if editing:
        await Form.confirm.set()
        await show_preview(callback_query.message, state)
    else:
        await Form.overstay.set()
        await callback_query.message.answer(
            "26. Были у вас exit permit или превышения пребывания в Индии "
            "90 дней за 1 въезд или 180 дней в году?",
            reply_markup=yes_no_kb("overstay"),
        )


@dp.callback_query_handler(lambda c: c.data.startswith("overstay:"), state=Form.overstay)
async def form_overstay(callback_query: CallbackQuery, state: FSMContext):
    ans = callback_query.data.split(":", 1)[1]
    value = "Да" if ans == "yes" else "Нет"
    await state.update_data(overstay=value)
    await callback_query.answer(value)

    await Form.confirm.set()
    await show_preview(callback_query.message, state)


# ---------- ПРЕДПРОСМОТР / ОТПРАВКА / РЕДАКТИРОВАНИЕ ----------

@dp.callback_query_handler(lambda c: c.data == "confirm:send", state=Form.confirm)
async def confirm_send(callback_query: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    user = callback_query.from_user

    app_id = save_application(
        user_id=user.id,
        username=user.username or "",
        data=data,
    )

    await state.finish()

    await callback_query.message.answer(
        f"Спасибо! Ваша анкета №{app_id} отправлена на проверку администратору.",
        reply_markup=admin_main_kb if is_admin(user.id) else user_main_kb,
    )

    await callback_query.answer("Анкета отправлена.")
    await notify_admins_about_application(app_id)


@dp.callback_query_handler(lambda c: c.data == "confirm:edit", state=Form.confirm)
async def confirm_edit(callback_query: CallbackQuery, state: FSMContext):
    await state.update_data(editing=True)
    await callback_query.message.answer(
        "Выберите, какой вопрос вы хотите отредактировать:",
        reply_markup=edit_menu_kb(),
    )
    await callback_query.answer()


@dp.callback_query_handler(lambda c: c.data.startswith("edit:"), state=Form.confirm)
async def edit_field(callback_query: CallbackQuery, state: FSMContext):
    field = callback_query.data.split(":", 1)[1]

    if field == "full_name":
        await Form.full_name.set()
        await callback_query.message.answer("Ваше ФИО (Фамилия Имя Отчество):")
    elif field == "place_birth":
        await Form.place_birth.set()
        await callback_query.message.answer(
            "1. Место вашего рождения (город/село/область):"
        )
    elif field == "email":
        await Form.email.set()
        await callback_query.message.answer("2. Ваша электронная почта:")
    elif field == "passport_number":
        await Form.passport_number.set()
        await callback_query.message.answer("3. Номер национального паспорта:")
    elif field == "home_address":
        await Form.home_address.set()
        await callback_query.message.answer(
            "4. Домашний адрес (Город, улица, номер дома, квартира, индекс):"
        )
    elif field == "phone":
        await Form.phone.set()
        await callback_query.message.answer("5. Ваш номер телефона:")
    elif field == "father_name":
        await Form.father_name.set()
        await callback_query.message.answer("6. Фамилия, имя отца (даже если нет в живых):")
    elif field == "father_birth_place":
        await Form.father_birth_place.set()
        await callback_query.message.answer("7. Место рождения отца:")
    elif field == "mother_name":
        await Form.mother_name.set()
        await callback_query.message.answer("8. Фамилия, имя матери (даже если нет в живых):")
    elif field == "mother_birth_place":
        await Form.mother_birth_place.set()
        await callback_query.message.answer("8. Место рождения матери:")
    elif field == "marital_status":
        await Form.marital_status.set()
        await callback_query.message.answer("9. Ваше семейное положение:")
    elif field == "spouse_name":
        await Form.spouse_name.set()
        await callback_query.message.answer(
            "10. Если вы в браке, укажите фамилию и имя вашего супруга(и). "
            "Если не в браке, напишите «нет»:"
        )
    elif field == "spouse_birth_place":
        await Form.spouse_birth_place.set()
        await callback_query.message.answer(
            "11. Место рождения вашего супруга(и). "
            "Если не в браке, напишите «нет»:"
        )
    elif field == "work_place":
        await Form.work_place.set()
        await callback_query.message.answer(
            "12. Название вашего места работы "
            "(если не работаете, напишите «безработный(ая)»):"
        )
    elif field == "work_address":
        await Form.work_address.set()
        await callback_query.message.answer(
            "13. Адрес вашего места работы "
            "(если не работаете, напишите «безработный(ая)»):"
        )
    elif field == "airport":
        await Form.airport.set()
        await callback_query.message.answer(
            "14. Аэропорт или порт планируемого прибытия в Индию:",
            reply_markup=airport_kb(),
        )
    elif field == "visa_term":
        await Form.visa_term.set()
        await callback_query.message.answer(
            "15. На какой срок нужна виза:",
            reply_markup=visa_term_kb(),
        )
    elif field == "arrival_date":
        await Form.arrival_date.set()
        await callback_query.message.answer(
            "16. Дата планируемого прибытия в Индию:",
            reply_markup=create_calendar(),
        )
    elif field == "contact_name":
        await Form.contact_name.set()
        await callback_query.message.answer("17. Фамилия и имя контактного лица в России:")
    elif field == "contact_phone":
        await Form.contact_phone.set()
        await callback_query.message.answer("18. Телефон контактного лица в России:")
    elif field == "contact_address":
        await Form.contact_address.set()
        await callback_query.message.answer("19. Адрес контактного лица в России:")
    elif field == "hotel_booked":
        await Form.hotel_booked.set()
        await callback_query.message.answer(
            "20. Если забронирован отель, выберите «Да». Если нет — «Нет»:",
            reply_markup=yes_no_kb("hotel"),
        )
    elif field == "five_year_visa":
        await Form.five_year_visa.set()
        await callback_query.message.answer(
            "21. Были ли у вас 5-летние визы в Индию?",
            reply_markup=yes_no_kb("fivevisa"),
        )
    elif field == "visa_refusal":
        await Form.visa_refusal.set()
        await callback_query.message.answer(
            "22. Были ли у вас отказы по визе в Индию:",
            reply_markup=yes_no_kb("vref"),
        )
    elif field == "trips_last_5y":
        await Form.trips_last_5y.set()
        await callback_query.message.answer(
            "23. Если были поездки в Индию за последние 5 лет, "
            "укажите даты и цель поездок:"
        )
    elif field == "last_visa_details":
        await Form.last_visa_details.set()
        await callback_query.message.answer(
            "24. Номер последней визы, дата выдачи последней визы, "
            "адрес проживания по последней поездке:"
        )
    elif field == "outside_india":
        await Form.outside_india.set()
        await callback_query.message.answer(
            "25. В момент оформления вы находитесь за пределами Индии?",
            reply_markup=yes_no_kb("outindia"),
        )
    elif field == "overstay":
        await Form.overstay.set()
        await callback_query.message.answer(
            "26. Были у вас exit permit или превышения пребывания в Индии "
            "90 дней за 1 въезд или 180 дней в году?",
            reply_markup=yes_no_kb("overstay"),
        )

    await callback_query.answer()


# ===================== АДМИН-ПАНЕЛЬ =====================

@dp.message_handler(lambda m: m.text == "Админ-панель")
async def admin_panel(message: types.Message):
    if not is_admin(message.from_user.id):
        await message.answer("Админ-панель доступна только администраторам.")
        return
    await message.answer("Админ-панель:", reply_markup=admin_panel_kb())


@dp.callback_query_handler(lambda c: c.data == "admin:new")
async def admin_new(callback_query: CallbackQuery):
    if not is_admin(callback_query.from_user.id):
        await callback_query.answer("Нет доступа", show_alert=True)
        return

    apps = list_applications(only_pending=True, limit=20)
    if not apps:
        await callback_query.message.answer("Новых заявок нет.")
    else:
        for app in apps:
            uname = f"@{app['username']}" if app["username"] else "без username"
            status = app["status"] or "в ожидании"
            text = (
                f"Заявка №{app['id']} от {app['created_at']}\n"
                f"Пользователь: {uname}\n"
                f"Статус: {status}"
            )
            kb = InlineKeyboardMarkup().add(
                InlineKeyboardButton(
                    "Открыть", callback_data=f"admin:open:{app['id']}"
                )
            )
            await callback_query.message.answer(text, reply_markup=kb)

    await callback_query.answer()


@dp.callback_query_handler(lambda c: c.data == "admin:all")
async def admin_all(callback_query: CallbackQuery):
    if not is_admin(callback_query.from_user.id):
        await callback_query.answer("Нет доступа", show_alert=True)
        return

    apps = list_applications(only_pending=False, limit=20)
    if not apps:
        await callback_query.message.answer("Заявок пока нет.")
    else:
        for app in apps:
            uname = f"@{app['username']}" if app["username"] else "без username"
            status = app["status"] or "в ожидании"
            text = (
                f"Заявка №{app['id']} от {app['created_at']}\n"
                f"Пользователь: {uname}\n"
                f"Статус: {status}"
            )
            kb = InlineKeyboardMarkup().add(
                InlineKeyboardButton(
                    "Открыть", callback_data=f"admin:open:{app['id']}"
                )
            )
            await callback_query.message.answer(text, reply_markup=kb)

    await callback_query.answer()


@dp.callback_query_handler(lambda c: c.data.startswith("admin:open:"))
async def admin_open(callback_query: CallbackQuery):
    if not is_admin(callback_query.from_user.id):
        await callback_query.answer("Нет доступа", show_alert=True)
        return

    try:
        app_id = int(callback_query.data.split(":", 2)[2])
    except ValueError:
        await callback_query.answer("Ошибка ID", show_alert=True)
        return

    app = get_application(app_id)
    if not app:
        await callback_query.answer("Заявка не найдена", show_alert=True)
        return

    text = format_application_text(app)
    await callback_query.message.answer(text, reply_markup=admin_application_kb(app_id))
    await callback_query.answer()


@dp.callback_query_handler(lambda c: c.data.startswith("approve:"))
async def admin_approve(callback_query: CallbackQuery):
    if not is_admin(callback_query.from_user.id):
        await callback_query.answer("Нет доступа", show_alert=True)
        return

    try:
        app_id = int(callback_query.data.split(":", 1)[1])
    except ValueError:
        await callback_query.answer("Ошибка ID", show_alert=True)
        return

    app = get_application(app_id)
    if not app:
        await callback_query.answer("Заявка не найдена", show_alert=True)
        return

    update_application_status(app_id, "одобрена", callback_query.from_user.id)
    await callback_query.answer("Анкета одобрена.")

    try:
        await bot.send_message(
            app["user_id"],
            f"Ваша анкета №{app_id} одобрена.",
        )
    except Exception as e:
        logging.warning(f"Не удалось отправить уведомление пользователю: {e}")


@dp.callback_query_handler(lambda c: c.data.startswith("reject:"))
async def admin_reject(callback_query: CallbackQuery):
    if not is_admin(callback_query.from_user.id):
        await callback_query.answer("Нет доступа", show_alert=True)
        return

    try:
        app_id = int(callback_query.data.split(":", 1)[1])
    except ValueError:
        await callback_query.answer("Ошибка ID", show_alert=True)
        return

    app = get_application(app_id)
    if not app:
        await callback_query.answer("Заявка не найдена", show_alert=True)
        return

    update_application_status(app_id, "отклонена", callback_query.from_user.id)
    await callback_query.answer("Анкета отклонена.")

    try:
        await bot.send_message(
            app["user_id"],
            f"Ваша анкета №{app_id} отклонена. "
            "При необходимости свяжитесь с администратором.",
        )
    except Exception as e:
        logging.warning(f"Не удалось отправить уведомление пользователю: {e}")


@dp.callback_query_handler(lambda c: c.data.startswith("msguser:"))
async def admin_msg_user(callback_query: CallbackQuery, state: FSMContext):
    if not is_admin(callback_query.from_user.id):
        await callback_query.answer("Нет доступа", show_alert=True)
        return

    try:
        app_id = int(callback_query.data.split(":", 1)[1])
    except ValueError:
        await callback_query.answer("Ошибка ID", show_alert=True)
        return

    app = get_application(app_id)
    if not app:
        await callback_query.answer("Заявка не найдена", show_alert=True)
        return

    target_user_id = app["user_id"]

    await AdminDialog.waiting_for_text.set()
    await state.update_data(target_user_id=target_user_id)
    await callback_query.message.answer(
        f"Напишите сообщение, которое нужно отправить пользователю "
        f"(@{app['username'] or 'без username'}). Оно будет отправлено от имени бота."
    )
    await callback_query.answer()


@dp.message_handler(state=AdminDialog.waiting_for_text, content_types=types.ContentTypes.TEXT)
async def admin_send_text_to_user(message: types.Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        await message.answer("Только администратор может отправлять такие сообщения.")
        await state.finish()
        return

    data = await state.get_data()
    target_user_id = data.get("target_user_id")
    if not target_user_id:
        await message.answer("Ошибка: не выбран получатель.")
        await state.finish()
        return

    try:
        await bot.send_message(
            target_user_id,
            "Сообщение от администратора:\n\n" + message.text.strip(),
        )
        await message.answer("Сообщение отправлено пользователю.")
    except Exception as e:
        logging.warning(f"Не удалось отправить сообщение пользователю: {e}")
        await message.answer("Не удалось отправить сообщение пользователю.")

    await state.finish()


@dp.callback_query_handler(lambda c: c.data == "admin:admins")
async def admin_list_admins(callback_query: CallbackQuery):
    if not is_admin(callback_query.from_user.id):
        await callback_query.answer("Нет доступа", show_alert=True)
        return

    admins = get_admins()
    if not admins:
        await callback_query.message.answer("Администраторы не найдены.")
    else:
        lines = ["Список администраторов:"]
        for adm in admins:
            uname = f"@{adm['username']}" if adm["username"] else "без username"
            marker = " (главный)" if adm["is_superadmin"] == 1 else ""
            lines.append(f"- {uname} (ID {adm['user_id']}){marker}")
        await callback_query.message.answer("\n".join(lines))

    await callback_query.answer()


@dp.callback_query_handler(lambda c: c.data.startswith("makeadmin:"))
async def admin_make_admin(callback_query: CallbackQuery):
    if not is_superadmin(callback_query.from_user.id):
        await callback_query.answer(
            "Только главный администратор может назначать админов.",
            show_alert=True,
        )
        return

    try:
        app_id = int(callback_query.data.split(":", 1)[1])
    except ValueError:
        await callback_query.answer("Ошибка ID", show_alert=True)
        return

    app = get_application(app_id)
    if not app:
        await callback_query.answer("Заявка не найдена", show_alert=True)
        return

    target_user_id = app["user_id"]
    target_username = app["username"] or ""

    upsert_admin(target_user_id, target_username, is_super=False)
    await callback_query.answer("Пользователь назначен администратором.")

    try:
        await bot.send_message(
            target_user_id,
            "Вы назначены администратором бота. "
            "Перезапустите диалог с помощью /start, чтобы увидеть админ-панель.",
        )
    except Exception as e:
        logging.warning(f"Не удалось уведомить нового админа: {e}")


# ===================== ЗАПУСК =====================

if __name__ == "__main__":
    init_db()
    executor.start_polling(dp, skip_updates=True)