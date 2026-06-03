const TRANSLATIONS = {
  uz: {
    // Auth / identity
    loading:               "Tasdiqlanmoqda...",
    restricted_title:      "Kirish cheklangan",
    restricted_msg:        "Tizim sizni aniqlay olmadi. Iltimos, korporativ tarmoq orqali kiring.",
    archived_title:        "Hujjat arxivlangan",
    archived_msg:          "Ushbu hujjat arxivlangan va endi mavjud emas. Savollar bo'lsa administrator bilan bog'laning.",
    notfound_title:        "Hujjat topilmadi",
    notfound_msg:          "Bunday hujjat mavjud emas yoki havola noto'g'ri. Savollar bo'lsa administrator bilan bog'laning.",
    confirm_title:         "Shaxsingizni tasdiqlang",
    confirm_subtitle:      "Quyidagi ma'lumotlar to'g'rimi?",
    field_name:            "Ism Familiya",
    field_dept:            "Tarkibiy tuzilma",
    field_position:        "Lavozim",
    btn_confirm:           "Ha, bu men",
    btn_decline:           "Yo'q, bu men emas",

    // AD login (document flow)
    login_ad_title:        "Tizimga kiring",
    login_ad_sub:          "Hujjat bilan tanishish uchun korporativ hisobingiz bilan kiring.",
    login_username_ph:     "ism.familiya",
    login_invalid:         "Login yoki parol noto'g'ri",
    attempt_word:          "Urinish",
    relogin_msg:           "Iltimos, ma'lumotlaringizni qayta kiriting",

    // Viewer
    viewer_title:          "Hujjat bilan tanishish",
    viewer_timer:          "Minimal vaqt",
    viewer_read:           "O'qildi",
    viewer_sec:            "soniya",
    viewer_user:           "Foydalanuvchi",
    viewer_no_preview:     "Ushbu fayl turi uchun ko'rish mavjud emas.",
    btn_download:          "Yuklab olish",
    btn_acknowledge:       "Tanishib chiqdim",
    ack_popup_title:       "Tasdiqlash",
    ack_popup_msg:         "Ushbu amal qayd etiladi. Davom etasizmi?",
    btn_yes:               "Ha, tasdiqlash",
    btn_no:                "Bekor qilish",
    scroll_warn:           "Hujjatni to'liq o'qing (90%)",
    time_warn:             "Minimal vaqtni kuting",

    // Final
    final_title:           "Rahmat!",
    final_msg:             "Vaqt ajratganingiz uchun rahmat!",
    final_sub:             "Hujjat bilan tanishganingiz qayd etildi.",
    final_info:            "Ma'lumot",

    // Statuses
    status_OPENED:                     "Hujjat ochilgan",
    status_ACKNOWLEDGED:               "Tanishib chiqilgan",

    // Admin general
    admin_panel:           "Admin Panel",
    admin_documents:       "Hujjatlar",
    admin_upload:          "Yuklash",
    admin_management:      "Boshqaruv",
    admin_logout:          "Chiqish",
    admin_archive:         "Arxiv",
    admin_archive_list:    "Arxivlangan hujjatlar",
    admin_no_archive:      "Arxivda hujjat yo'q.",
    admin_restore:         "Tiklash",
    archive_title:         "Hujjatni arxivlash",
    archive_msg:           "\"{title}\" arxivga o'tkaziladi. Ma'lumotlar saqlanadi, istalgan vaqt tiklash mumkin.",
    restore_title:         "Hujjatni tiklash",
    restore_msg:           "\"{title}\" arxivdan Hujjatlarga qaytariladi.",
    action_failed:         "Amal bajarilmadi.",
    admin_doc_list:        "Hujjatlar ro'yxati",
    admin_stats_total:     "Jami hujjatlar",
    admin_stats_ack:       "Tanishib chiqqanlar",
    admin_stats_users:     "Jami foydalanuvchilar",
    admin_stats_ad_users:      "AD jami xodimlar",
    admin_stats_depts:         "Tarkibiy tuzilmalar",
    admin_stats_system_users:  "Tizimdan foydalanganlar",
    admin_stats_ack_employees: "Tanishgan xodimlar",
    admin_stats_coverage:      "Qamrov foizi",
    chart_donut:               "Tanishish holati (AD bo'yicha)",
    chart_dept:                "Bo'limlar bo'yicha tanishgan",
    chart_daily:               "So'nggi 30 kun — kunlik tanishish",
    chart_ack:                 "Tanishgan",
    chart_not_ack:             "Tanishmagan",

    // Admin table
    admin_name:            "Ism",
    admin_dept:            "Bo'lim",
    admin_status:          "Holat",
    admin_opened:          "Ochildi",
    admin_confirmed:       "Tasdiqlandi",
    admin_acknowledged:    "Tanishib chiqdi",
    admin_file:            "Fayl",
    admin_uploaded:        "Yuklangan",
    admin_records:         "ta yozuv",
    admin_title_col:       "Sarlavha",
    admin_view_file:       "Ko'rish",
    admin_employees:       "Xodimlar",
    admin_people:          "ta",
    admin_attempts:        "Urinishlar",
    live:                  "jonli",
    col_dept:              "Tarkibiy tuzilma",
    col_position:          "Lavozim",
    col_time:              "Vaqti",
    col_ip:                "IP manzil",

    // Dialog
    dialog_yes:            "Ha",
    dialog_no:             "Bekor qilish",
    dialog_confirm_title:  "Tasdiqlang",
    dialog_notice:         "Ma'lumot",
    delete_title:          "Hujjatni o'chirish",
    delete_msg:            "\"{title}\" hujjati o'chiriladi. Bu amalni qaytarib bo'lmaydi.",
    delete_confirm:        "O'chirish",
    delete_failed:         "O'chirib bo'lmadi.",

    // Admin export / filter
    admin_export_csv:      "CSV yuklash",
    admin_export_excel:    "Excel yuklash",
    admin_filter:          "Filtrlash",
    admin_all_statuses:    "Barcha holatlar",
    admin_all_depts:       "Barcha bo'limlar",
    admin_reset:           "Tozalash",
    admin_back:            "← Orqaga",
    admin_no_docs:         "Hujjatlar mavjud emas.",
    admin_no_records:      "Yozuvlar topilmadi",

    // Admin upload
    admin_upload_title:    "Hujjat yuklash",
    admin_upload_label:    "Sarlavha",
    admin_upload_file:     "Fayl",
    admin_upload_hint:     "PDF, Word, Excel, rasm va boshqa formatlar",
    admin_upload_btn:      "Yuklash →",
    admin_uploaded_ok:     "Hujjat yuklandi!",
    admin_upload_again:    "Yana yuklash",
    upload_drag:           "Faylni shu yerga sudrab tashlang",
    upload_browse:         "yoki tanlang",
    upload_remove:         "O'chirish",

    // Share link
    share_link:            "Ulashish havolasi",
    copy_link:             "Nusxa olish",
    copied:                "Nusxalandi!",

    // Brand
    brand_subtitle:        "Hujjatlar bilan tanishish tizimi",
    doc_banner_label:      "Hujjat",
    // Login
    login_title:           "Admin Panel",
    login_sub:             "Agrobank ACK tizimi",
    login_username:        "Login",
    login_password:        "Parol",
    login_btn:             "Kirish",
    login_error:           "Login yoki parol noto'g'ri",

    // Lang
    lang_switch:           "RU",
  },

  ru: {
    // Auth / identity
    loading:               "Подтверждение...",
    restricted_title:      "Доступ ограничен",
    restricted_msg:        "Система не смогла вас идентифицировать. Пожалуйста, войдите через корпоративную сеть.",
    archived_title:        "Документ архивирован",
    archived_msg:          "Этот документ архивирован и больше недоступен. По вопросам обратитесь к администратору.",
    notfound_title:        "Документ не найден",
    notfound_msg:          "Такого документа не существует или ссылка неверна. По вопросам обратитесь к администратору.",
    confirm_title:         "Подтвердите личность",
    confirm_subtitle:      "Следующие данные верны?",
    field_name:            "Имя и фамилия",
    field_dept:            "Структурное подразделение",
    field_position:        "Должность",
    btn_confirm:           "Да, это я",
    btn_decline:           "Нет, это не я",

    // AD login (document flow)
    login_ad_title:        "Войдите в систему",
    login_ad_sub:          "Войдите под своей корпоративной учётной записью для ознакомления с документом.",
    login_username_ph:     "имя.фамилия",
    login_invalid:         "Неверный логин или пароль",
    attempt_word:          "Попытка",
    relogin_msg:           "Пожалуйста, введите данные заново",

    // Viewer
    viewer_title:          "Ознакомление с документом",
    viewer_timer:          "Мин. время",
    viewer_read:           "Прочитано",
    viewer_sec:            "сек.",
    viewer_user:           "Пользователь",
    viewer_no_preview:     "Для этого типа файла предпросмотр недоступен.",
    btn_download:          "Скачать",
    btn_acknowledge:       "Ознакомился",
    ack_popup_title:       "Подтверждение",
    ack_popup_msg:         "Это действие будет зафиксировано. Продолжить?",
    btn_yes:               "Да, подтвердить",
    btn_no:                "Отмена",
    scroll_warn:           "Прокрутите документ до конца (90%)",
    time_warn:             "Дождитесь истечения минимального времени",

    // Final
    final_title:           "Спасибо!",
    final_msg:             "Спасибо за ваше время!",
    final_sub:             "Факт ознакомления с документом зафиксирован.",
    final_info:            "Информация",

    // Statuses
    status_OPENED:                     "Документ открыт",
    status_ACKNOWLEDGED:               "Ознакомлен",

    // Admin general
    admin_panel:           "Панель администратора",
    admin_documents:       "Документы",
    admin_upload:          "Загрузить",
    admin_management:      "Управление",
    admin_logout:          "Выход",
    admin_archive:         "Архив",
    admin_archive_list:    "Архивированные документы",
    admin_no_archive:      "В архиве нет документов.",
    admin_restore:         "Восстановить",
    archive_title:         "Архивировать документ",
    archive_msg:           "\"{title}\" будет перемещён в архив. Данные сохранятся, можно восстановить в любой момент.",
    restore_title:         "Восстановить документ",
    restore_msg:           "\"{title}\" будет возвращён из архива в Документы.",
    action_failed:         "Не удалось выполнить.",
    admin_doc_list:        "Список документов",
    admin_stats_total:     "Всего документов",
    admin_stats_ack:       "Ознакомились",
    admin_stats_users:     "Всего пользователей",
    admin_stats_ad_users:      "Всего сотрудников (AD)",
    admin_stats_depts:         "Структурные подразделения",
    admin_stats_system_users:  "Воспользовались системой",
    admin_stats_ack_employees: "Ознакомленные",
    admin_stats_coverage:      "Процент охвата",
    chart_donut:               "Статус ознакомления (по AD)",
    chart_dept:                "Ознакомления по отделам",
    chart_daily:               "Последние 30 дней — по дням",
    chart_ack:                 "Ознакомлены",
    chart_not_ack:             "Не ознакомлены",

    // Admin table
    admin_name:            "Имя",
    admin_dept:            "Отдел",
    admin_status:          "Статус",
    admin_opened:          "Открыт",
    admin_confirmed:       "Подтверждён",
    admin_acknowledged:    "Ознакомился",
    admin_file:            "Файл",
    admin_uploaded:        "Загружен",
    admin_records:         "записей",
    admin_title_col:       "Название",
    admin_view_file:       "Просмотр",
    admin_employees:       "Сотрудники",
    admin_people:          "чел.",
    admin_attempts:        "Попытки",
    live:                  "в реальном времени",
    col_dept:              "Структурное подразделение",
    col_position:          "Должность",
    col_time:              "Время",
    col_ip:                "IP адрес",

    // Dialog
    dialog_yes:            "Да",
    dialog_no:             "Отмена",
    dialog_confirm_title:  "Подтвердите",
    dialog_notice:         "Информация",
    delete_title:          "Удалить документ",
    delete_msg:            "Документ \"{title}\" будет удалён. Это действие необратимо.",
    delete_confirm:        "Удалить",
    delete_failed:         "Не удалось удалить.",

    // Admin export / filter
    admin_export_csv:      "Экспорт CSV",
    admin_export_excel:    "Экспорт Excel",
    admin_filter:          "Фильтр",
    admin_all_statuses:    "Все статусы",
    admin_all_depts:       "Все отделы",
    admin_reset:           "Сбросить",
    admin_back:            "← Назад",
    admin_no_docs:         "Документов нет.",
    admin_no_records:      "Записи не найдены",

    // Admin upload
    admin_upload_title:    "Загрузить документ",
    admin_upload_label:    "Название",
    admin_upload_file:     "Файл",
    admin_upload_hint:     "PDF, Word, Excel, изображения и другие форматы",
    admin_upload_btn:      "Загрузить →",
    admin_uploaded_ok:     "Документ загружен!",
    admin_upload_again:    "Загрузить ещё",
    upload_drag:           "Перетащите файл сюда",
    upload_browse:         "или выберите",
    upload_remove:         "Удалить",

    // Share link
    share_link:            "Ссылка для отправки",
    copy_link:             "Скопировать",
    copied:                "Скопировано!",

    // Brand
    brand_subtitle:        "Система ознакомления с документами",
    doc_banner_label:      "Документ",
    // Login
    login_title:           "Панель администратора",
    login_sub:             "Система Agrobank ACK",
    login_username:        "Логин",
    login_password:        "Пароль",
    login_btn:             "Войти",
    login_error:           "Неверный логин или пароль",

    // Lang
    lang_switch:           "UZ",
  },
};

const I18n = (() => {
  const STORAGE_KEY = "ack_lang";
  let current = localStorage.getItem(STORAGE_KEY) || "uz";

  function t(key) {
    return (TRANSLATIONS[current] || TRANSLATIONS.uz)[key] || key;
  }

  function setLang(lang) {
    if (!TRANSLATIONS[lang]) return;
    current = lang;
    localStorage.setItem(STORAGE_KEY, lang);
    applyAll();
    updateToggles();
  }

  function getLang() { return current; }

  function applyAll() {
    document.querySelectorAll("[data-i18n]").forEach((el) => {
      el.textContent = t(el.getAttribute("data-i18n"));
    });
    document.querySelectorAll("[data-i18n-ph]").forEach((el) => {
      el.placeholder = t(el.getAttribute("data-i18n-ph"));
    });
    document.querySelectorAll("[data-i18n-title]").forEach((el) => {
      el.title = t(el.getAttribute("data-i18n-title"));
    });
  }

  function updateToggles() {
    document.querySelectorAll(".lang-toggle").forEach(btn => {
      btn.textContent = t("lang_switch");
    });
  }

  function toggle() {
    setLang(current === "uz" ? "ru" : "uz");
  }

  function init() {
    applyAll();
    updateToggles();
    document.querySelectorAll(".lang-toggle").forEach(btn => {
      btn.addEventListener("click", toggle);
    });
  }

  // Run now if the document is already parsed (e.g. page injected via
  // document.write), otherwise wait for DOMContentLoaded.
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }

  return { t, setLang, getLang, toggle };
})();
