/* Noel Chauffer — site translations + language switcher runtime.
   Languages: en (English US), es (Spanish), fr (French), ar (Arabic),
   pt (Portuguese), ur (Roman Urdu), hi (Hindi), bn (Bengali),
   ud (Urdu), zh (Chinese Simplified), de (German), it (Italian),
   ru (Russian), tr (Turkish), ko (Korean), ja (Japanese),
   vi (Vietnamese), fa (Persian), th (Thai).
   Class names (Business Class / Business SUV / First Class) stay English
   in every language — they are product names. Money, dates, addresses
   and airport codes are never translated. Arabic, Urdu and Persian
   are right-to-left.
   The choice persists in localStorage under "noel-language" and is
   shared by the website and the customer app (/app). */
var NOEL_I18N = {};

NOEL_I18N["menu.our_services"] = {
  "en": "Our services", "es": "Nuestros servicios", "fr": "Nos services", "ar": "خدماتنا",
  "pt": "Nossos serviços", "ur": "Hamari services", "hi": "हमारी सेवाएँ", "bn": "আমাদের পরিষেবা",
  "ud": "ہماری خدمات", "zh": "我们的服务", "de": "Unsere Dienstleistungen", "it": "I nostri servizi",
  "ru": "Наши услуги", "tr": "Hizmetlerimiz", "ko": "서비스 소개", "ja": "私たちのサービス",
  "vi": "Dịch vụ của chúng tôi", "fa": "خدمات ما", "th": "บริการของเรา"
};

NOEL_I18N["menu.city_to_city"] = {
  "en": "City-to-City rides", "es": "Viajes de ciudad a ciudad", "fr": "Trajets de ville à ville", "ar": "رحلات من مدينة إلى مدينة",
  "pt": "Viagens de cidade a cidade", "ur": "City-to-City rides", "hi": "शहर से शहर की सवारी", "bn": "শহর থেকে শহরে রাইড",
  "ud": "شہر سے شہر سفر", "zh": "城际行程", "de": "Fahrten von Stadt zu Stadt", "it": "Corse da città a città",
  "ru": "Поездки из города в город", "tr": "Şehirlerarası yolculuklar", "ko": "도시 간 이동", "ja": "都市間乗車",
  "vi": "Chuyến đi liên thành phố", "fa": "سفر بین‌شهری", "th": "การเดินทางระหว่างเมือง"
};

NOEL_I18N["menu.chauffeur_hailing"] = {
  "en": "Chauffeur hailing", "es": "Chófer a pedido", "fr": "Chauffeur à la demande", "ar": "استدعاء سائق",
  "pt": "Motorista sob demanda", "ur": "Chauffeur hailing", "hi": "शॉफ़र हेलिंग", "bn": "শোফার হেইলিং",
  "ud": "ڈرائیور بلانا", "zh": "叫车服务", "de": "Chauffeur auf Abruf", "it": "Chauffeur a chiamata",
  "ru": "Вызов шофёра", "tr": "Şoför çağırma", "ko": "쇼퍼 호출", "ja": "ショファー呼び出し",
  "vi": "Gọi tài xế", "fa": "فراخوانی راننده", "th": "เรียกคนขับ"
};

NOEL_I18N["menu.airport_transfers"] = {
  "en": "Airport transfers", "es": "Traslados al aeropuerto", "fr": "Transferts aéroport", "ar": "النقل من وإلى المطار",
  "pt": "Transfers de aeroporto", "ur": "Airport transfers", "hi": "एयरपोर्ट ट्रांसफर", "bn": "বিমানবন্দর ট্রান্সফার",
  "ud": "ہوائی اڈے کی منتقلی", "zh": "机场接送", "de": "Flughafentransfers", "it": "Trasferimenti aeroportuali",
  "ru": "Трансферы в аэропорт", "tr": "Havalimanı transferleri", "ko": "공항 이동", "ja": "空港送迎",
  "vi": "Đưa đón sân bay", "fa": "ترانسفر فرودگاه", "th": "รับส่งสนามบิน"
};

NOEL_I18N["menu.hourly_hire"] = {
  "en": "Hourly hire", "es": "Alquiler por horas", "fr": "Location à l'heure", "ar": "الحجز بالساعة",
  "pt": "Aluguel por hora", "ur": "Hourly hire", "hi": "घंटे के हिसाब से किराया", "bn": "ঘণ্টা হিসেবে ভাড়া",
  "ud": "فی گھنٹہ کرایہ", "zh": "按小时租用", "de": "Stundenweise Miete", "it": "Noleggio a ore",
  "ru": "Почасовая аренда", "tr": "Saatlik kiralama", "ko": "시간제 대여", "ja": "時間貸し",
  "vi": "Thuê theo giờ", "fa": "کرایهٔ ساعتی", "th": "เช่ารายชั่วโมง"
};

NOEL_I18N["menu.chauffeur_service"] = {
  "en": "Chauffeur service", "es": "Servicio de chófer", "fr": "Service de chauffeur", "ar": "خدمة السائق",
  "pt": "Serviço de motorista", "ur": "Chauffeur service", "hi": "शॉफ़र सेवा", "bn": "শোফার পরিষেবা",
  "ud": "ڈرائیور سروس", "zh": "专车服务", "de": "Chauffeurservice", "it": "Servizio chauffeur",
  "ru": "Услуги шофёра", "tr": "Şoför hizmeti", "ko": "쇼퍼 서비스", "ja": "ショファーサービス",
  "vi": "Dịch vụ tài xế", "fa": "خدمات راننده", "th": "บริการคนขับ"
};

NOEL_I18N["menu.limousine"] = {
  "en": "Limousine service", "es": "Servicio de limusina", "fr": "Service de limousine", "ar": "خدمة الليموزين",
  "pt": "Serviço de limusine", "ur": "Limousine service", "hi": "लिमोज़िन सेवा", "bn": "লিমুজিন পরিষেবা",
  "ud": "لمیوزین سروس", "zh": "豪华轿车服务", "de": "Limousinenservice", "it": "Servizio limousine",
  "ru": "Услуги лимузина", "tr": "Limuzin hizmeti", "ko": "리무진 서비스", "ja": "リムジンサービス",
  "vi": "Dịch vụ limousine", "fa": "خدمات لیموزین", "th": "บริการลีมูซีน"
};

NOEL_I18N["menu.for_business"] = {
  "en": "For business", "es": "Para empresas", "fr": "Pour les entreprises", "ar": "للأعمال",
  "pt": "Para empresas", "ur": "Business ke liye", "hi": "व्यवसाय के लिए", "bn": "ব্যবসার জন্য",
  "ud": "کاروبار کے لیے", "zh": "企业服务", "de": "Für Unternehmen", "it": "Per le aziende",
  "ru": "Для бизнеса", "tr": "İşletmeler için", "ko": "비즈니스용", "ja": "ビジネス向け",
  "vi": "Cho doanh nghiệp", "fa": "برای کسب‌وکار", "th": "สำหรับธุรกิจ"
};

NOEL_I18N["menu.overview"] = {
  "en": "Overview", "es": "Resumen", "fr": "Aperçu", "ar": "نظرة عامة",
  "pt": "Visão geral", "ur": "Overview", "hi": "अवलोकन", "bn": "সংক্ষিপ্ত বিবরণ",
  "ud": "جائزہ", "zh": "概览", "de": "Überblick", "it": "Panoramica",
  "ru": "Обзор", "tr": "Genel bakış", "ko": "개요", "ja": "概要",
  "vi": "Tổng quan", "fa": "نمای کلی", "th": "ภาพรวม"
};

NOEL_I18N["menu.corporations"] = {
  "en": "Corporations", "es": "Empresas", "fr": "Entreprises", "ar": "الشركات",
  "pt": "Empresas", "ur": "Corporations", "hi": "कॉर्पोरेशन", "bn": "কর্পোরেশন",
  "ud": "کارپوریشنز", "zh": "企业", "de": "Unternehmen", "it": "Aziende",
  "ru": "Корпорации", "tr": "Şirketler", "ko": "기업", "ja": "法人",
  "vi": "Doanh nghiệp", "fa": "شرکت‌ها", "th": "องค์กร"
};

NOEL_I18N["menu.travel_agencies"] = {
  "en": "Travel agencies", "es": "Agencias de viajes", "fr": "Agences de voyages", "ar": "وكالات السفر",
  "pt": "Agências de viagens", "ur": "Travel agencies", "hi": "ट्रैवल एजेंसियाँ", "bn": "ট্রাভেল এজেন্সি",
  "ud": "ٹریول ایجنسیاں", "zh": "旅行社", "de": "Reisebüros", "it": "Agenzie di viaggio",
  "ru": "Туристические агентства", "tr": "Seyahat acenteleri", "ko": "여행사", "ja": "旅行代理店",
  "vi": "Đại lý du lịch", "fa": "آژانس‌های مسافرتی", "th": "ตัวแทนท่องเที่ยว"
};

NOEL_I18N["menu.partnerships"] = {
  "en": "Strategic partnerships", "es": "Alianzas estratégicas", "fr": "Partenariats stratégiques", "ar": "شراكات استراتيجية",
  "pt": "Parcerias estratégicas", "ur": "Strategic partnerships", "hi": "रणनीतिक साझेदारियाँ", "bn": "কৌশলগত অংশীদারিত্ব",
  "ud": "اسٹریٹجک شراکتیں", "zh": "战略合作", "de": "Strategische Partnerschaften", "it": "Partnership strategiche",
  "ru": "Стратегические партнёрства", "tr": "Stratejik ortaklıklar", "ko": "전략적 제휴", "ja": "戦略的パートナーシップ",
  "vi": "Đối tác chiến lược", "fa": "شراکت‌های راهبردی", "th": "พันธมิตรเชิงกลยุทธ์"
};

NOEL_I18N["menu.your_rides"] = {
  "en": "Your rides", "es": "Tus viajes", "fr": "Vos trajets", "ar": "رحلاتك",
  "pt": "Suas viagens", "ur": "Aapki rides", "hi": "आपकी सवारियाँ", "bn": "আপনার রাইডগুলো",
  "ud": "آپ کی سواریاں", "zh": "您的行程", "de": "Ihre Fahrten", "it": "Le tue corse",
  "ru": "Ваши поездки", "tr": "Yolculuklarınız", "ko": "고객님의 이동", "ja": "お客様の乗車",
  "vi": "Chuyến đi của bạn", "fa": "سفرهای شما", "th": "การเดินทางของคุณ"
};

NOEL_I18N["menu.help"] = {
  "en": "Help", "es": "Ayuda", "fr": "Aide", "ar": "مساعدة",
  "pt": "Ajuda", "ur": "Help", "hi": "सहायता", "bn": "সহায়তা",
  "ud": "مدد", "zh": "帮助", "de": "Hilfe", "it": "Aiuto",
  "ru": "Помощь", "tr": "Yardım", "ko": "도움말", "ja": "ヘルプ",
  "vi": "Trợ giúp", "fa": "راهنما", "th": "ช่วยเหลือ"
};

NOEL_I18N["menu.sign_in"] = {
  "en": "Sign in", "es": "Iniciar sesión", "fr": "Se connecter", "ar": "تسجيل الدخول",
  "pt": "Entrar", "ur": "Sign in", "hi": "साइन इन करें", "bn": "সাইন ইন করুন",
  "ud": "سائن ان کریں", "zh": "登录", "de": "Anmelden", "it": "Accedi",
  "ru": "Войти", "tr": "Giriş yap", "ko": "로그인", "ja": "サインイン",
  "vi": "Đăng nhập", "fa": "ورود", "th": "เข้าสู่ระบบ"
};

NOEL_I18N["menu.sign_out"] = {
  "en": "Sign out", "es": "Cerrar sesión", "fr": "Se déconnecter", "ar": "تسجيل الخروج",
  "pt": "Sair", "ur": "Sign out", "hi": "साइन आउट करें", "bn": "সাইন আউট করুন",
  "ud": "سائن آؤٹ کریں", "zh": "退出登录", "de": "Abmelden", "it": "Esci",
  "ru": "Выйти", "tr": "Çıkış yap", "ko": "로그아웃", "ja": "サインアウト",
  "vi": "Đăng xuất", "fa": "خروج", "th": "ออกจากระบบ"
};

NOEL_I18N["menu.signin_fill"] = {
  "en": "Please enter your email and phone number.", "es": "Introduce tu correo electrónico y tu número de teléfono.", "fr": "Veuillez saisir votre e-mail et votre numéro de téléphone.", "ar": "يرجى إدخال بريدك الإلكتروني ورقم هاتفك.",
  "pt": "Informe seu e-mail e número de telefone.", "ur": "Apna email aur phone number likhen.", "hi": "कृपया अपना ईमेल और फ़ोन नंबर दर्ज करें।", "bn": "আপনার ইমেইল এবং ফোন নম্বর লিখুন।",
  "ud": "براہ کرم اپنا ای میل اور فون نمبر درج کریں", "zh": "请输入您的邮箱和电话号码。", "de": "Bitte geben Sie Ihre E-Mail-Adresse und Telefonnummer ein.", "it": "Inserisci la tua email e il numero di telefono.",
  "ru": "Пожалуйста, введите вашу электронную почту и номер телефона.", "tr": "Lütfen e-postanızı ve telefon numaranızı girin.", "ko": "이메일과 전화번호를 입력해 주세요.", "ja": "メールアドレスと電話番号を入力してください。",
  "vi": "Vui lòng nhập email và số điện thoại của bạn.", "fa": "لطفاً ایمیل و شماره تلفن خود را وارد کنید", "th": "โปรดป้อนอีเมลและหมายเลขโทรศัพท์ของคุณ"
};

NOEL_I18N["menu.open"] = {
  "en": "Open menu", "es": "Abrir menú", "fr": "Ouvrir le menu", "ar": "افتح القائمة",
  "pt": "Abrir menu", "ur": "Menu kholen", "hi": "मेनू खोलें", "bn": "মেনু খুলুন",
  "ud": "مینیو کھولیں", "zh": "打开菜单", "de": "Menü öffnen", "it": "Apri menu",
  "ru": "Открыть меню", "tr": "Menüyü aç", "ko": "메뉴 열기", "ja": "メニューを開く",
  "vi": "Mở menu", "fa": "باز کردن منو", "th": "เปิดเมนู"
};

NOEL_I18N["menu.close"] = {
  "en": "Close menu", "es": "Cerrar menú", "fr": "Fermer le menu", "ar": "أغلق القائمة",
  "pt": "Fechar menu", "ur": "Menu band karen", "hi": "मेनू बंद करें", "bn": "মেনু বন্ধ করুন",
  "ud": "مینیو بند کریں", "zh": "关闭菜单", "de": "Menü schließen", "it": "Chiudi menu",
  "ru": "Закрыть меню", "tr": "Menüyü kapat", "ko": "메뉴 닫기", "ja": "メニューを閉じる",
  "vi": "Đóng menu", "fa": "بستن منو", "th": "ปิดเมนู"
};

NOEL_I18N["menu.your_ride"] = {
  "en": "Your ride", "es": "Tu viaje", "fr": "Votre trajet", "ar": "رحلتك",
  "pt": "Sua viagem", "ur": "Aapki ride", "hi": "आपकी सवारी", "bn": "আপনার রাইড",
  "ud": "آپ کی سواری", "zh": "您的行程", "de": "Ihre Fahrt", "it": "La tua corsa",
  "ru": "Ваша поездка", "tr": "Yolculuğunuz", "ko": "고객님의 이동", "ja": "お客様の乗車",
  "vi": "Chuyến đi của bạn", "fa": "سفر شما", "th": "การเดินทางของคุณ"
};

NOEL_I18N["menu.why_us"] = {
  "en": "Why us", "es": "Por qué nosotros", "fr": "Pourquoi nous", "ar": "لماذا نحن",
  "pt": "Por que nós", "ur": "Hum kyun", "hi": "हम क्यों", "bn": "আমরা কেন",
  "ud": "ہم کیوں", "zh": "为什么选择我们", "de": "Warum wir", "it": "Perché noi",
  "ru": "Почему мы", "tr": "Neden biz", "ko": "선택 이유", "ja": "私たちが選ばれる理由",
  "vi": "Tại sao chọn chúng tôi", "fa": "چرا ما", "th": "ทำไมต้องเรา"
};

NOEL_I18N["menu.cancellation"] = {
  "en": "Cancellation & waiting", "es": "Cancelación y espera", "fr": "Annulation et attente", "ar": "الإلغاء والانتظار",
  "pt": "Cancelamento e espera", "ur": "Cancellation & waiting", "hi": "रद्दीकरण और प्रतीक्षा", "bn": "বাতিল ও অপেক্ষা",
  "ud": "منسوخی اور انتظار", "zh": "取消与等候", "de": "Stornierung & Wartezeit", "it": "Cancellazione e attesa",
  "ru": "Отмена и ожидание", "tr": "İptal ve bekleme", "ko": "취소 및 대기", "ja": "キャンセルと待ち時間",
  "vi": "Hủy xe và chờ đợi", "fa": "لغو و انتظار", "th": "การยกเลิกและการรอ"
};

NOEL_I18N["menu.faq"] = {
  "en": "FAQ", "es": "Preguntas frecuentes", "fr": "FAQ", "ar": "الأسئلة الشائعة",
  "pt": "Perguntas frequentes", "ur": "FAQ", "hi": "सामान्य प्रश्न", "bn": "সাধারণ প্রশ্ন",
  "ud": "عمومی سوالات", "zh": "常见问题", "de": "FAQ", "it": "FAQ",
  "ru": "FAQ", "tr": "SSS", "ko": "자주 묻는 질문", "ja": "よくある質問",
  "vi": "Câu hỏi thường gặp", "fa": "سؤالات متداول", "th": "คำถามที่พบบ่อย"
};

NOEL_I18N["menu.our_company"] = {
  "en": "Our company", "es": "Nuestra empresa", "fr": "Notre entreprise", "ar": "شركتنا",
  "pt": "Nossa empresa", "ur": "Hamari company", "hi": "हमारी कंपनी", "bn": "আমাদের কোম্পানি",
  "ud": "ہماری کمپنی", "zh": "我们公司", "de": "Unser Unternehmen", "it": "La nostra azienda",
  "ru": "Наша компания", "tr": "Şirketimiz", "ko": "회사 소개", "ja": "私たちの会社",
  "vi": "Công ty chúng tôi", "fa": "شرکت ما", "th": "บริษัทของเรา"
};

NOEL_I18N["menu.contacts"] = {
  "en": "Contacts", "es": "Contactos", "fr": "Contacts", "ar": "اتصل بنا",
  "pt": "Contatos", "ur": "Contacts", "hi": "संपर्क", "bn": "যোগাযোগ",
  "ud": "رابطہ", "zh": "联系方式", "de": "Kontakt", "it": "Contatti",
  "ru": "Контакты", "tr": "İletişim", "ko": "연락처", "ja": "お問い合わせ",
  "vi": "Liên hệ", "fa": "تماس", "th": "ติดต่อ"
};

NOEL_I18N["menu.ride_history"] = {
  "en": "Ride history", "es": "Historial de viajes", "fr": "Historique des trajets", "ar": "سجل الرحلات",
  "pt": "Histórico de viagens", "ur": "Ride history", "hi": "सवारी इतिहास", "bn": "রাইডের ইতিহাস",
  "ud": "سواری کی تاریخ", "zh": "行程记录", "de": "Fahrtenverlauf", "it": "Cronologia corse",
  "ru": "История поездок", "tr": "Yolculuk geçmişi", "ko": "이동 내역", "ja": "乗車履歴",
  "vi": "Lịch sử chuyến đi", "fa": "تاریخچهٔ سفر", "th": "ประวัติการเดินทาง"
};

NOEL_I18N["menu.experience"] = {
  "en": "Experience", "es": "Experiencia", "fr": "Expérience", "ar": "التجربة",
  "pt": "Experiência", "ur": "Experience", "hi": "अनुभव", "bn": "অভিজ্ঞতা",
  "ud": "تجربہ", "zh": "体验", "de": "Erlebnis", "it": "Esperienza",
  "ru": "Впечатление", "tr": "Deneyim", "ko": "경험", "ja": "エクスペリエンス",
  "vi": "Trải nghiệm", "fa": "تجربه", "th": "ประสบการณ์"
};

NOEL_I18N["form.your_ride"] = {
  "en": "Your ride", "es": "Tu viaje", "fr": "Votre trajet", "ar": "رحلتك",
  "pt": "Sua viagem", "ur": "Aapki ride", "hi": "आपकी सवारी", "bn": "আপনার রাইড",
  "ud": "آپ کی سواری", "zh": "您的行程", "de": "Ihre Fahrt", "it": "La tua corsa",
  "ru": "Ваша поездка", "tr": "Yolculuğunuz", "ko": "고객님의 이동", "ja": "お客様の乗車",
  "vi": "Chuyến đi của bạn", "fa": "سفر شما", "th": "การเดินทางของคุณ"
};

NOEL_I18N["form.one_way"] = {
  "en": "One way", "es": "Solo ida", "fr": "Aller simple", "ar": "اتجاه واحد",
  "pt": "Somente ida", "ur": "One way", "hi": "एक तरफा", "bn": "এক দিকে",
  "ud": "ایک طرفہ", "zh": "单程", "de": "Einfache Fahrt", "it": "Solo andata",
  "ru": "В одну сторону", "tr": "Tek yön", "ko": "편도", "ja": "片道",
  "vi": "Một chiều", "fa": "یک‌طرفه", "th": "เที่ยวเดียว"
};

NOEL_I18N["form.by_the_hour"] = {
  "en": "By the hour", "es": "Por horas", "fr": "À l'heure", "ar": "بالساعة",
  "pt": "Por hora", "ur": "By the hour", "hi": "घंटे के हिसाब से", "bn": "ঘণ্টা হিসেবে",
  "ud": "فی گھنٹہ", "zh": "按小时", "de": "Stundenweise", "it": "A ore",
  "ru": "Почасовая", "tr": "Saatlik", "ko": "시간제", "ja": "時間貸し",
  "vi": "Theo giờ", "fa": "ساعتی", "th": "รายชั่วโมง"
};

NOEL_I18N["form.select_date"] = {
  "en": "Select a date", "es": "Selecciona una fecha", "fr": "Sélectionnez une date", "ar": "اختر تاريخًا",
  "pt": "Selecione uma data", "ur": "Date chunen", "hi": "तारीख़ चुनें", "bn": "তারিখ বেছে নিন",
  "ud": "تاریخ منتخب کریں", "zh": "选择日期", "de": "Datum auswählen", "it": "Seleziona una data",
  "ru": "Выберите дату", "tr": "Bir tarih seçin", "ko": "날짜 선택", "ja": "日付を選択",
  "vi": "Chọn ngày", "fa": "تاریخ را انتخاب کنید", "th": "เลือกวันที่"
};

NOEL_I18N["form.select_time"] = {
  "en": "Select a time", "es": "Selecciona una hora", "fr": "Sélectionnez une heure", "ar": "اختر وقتًا",
  "pt": "Selecione um horário", "ur": "Time chunen", "hi": "समय चुनें", "bn": "সময় বেছে নিন",
  "ud": "وقت منتخب کریں", "zh": "选择时间", "de": "Uhrzeit auswählen", "it": "Seleziona un orario",
  "ru": "Выберите время", "tr": "Bir saat seçin", "ko": "시간 선택", "ja": "時刻を選択",
  "vi": "Chọn giờ", "fa": "زمان را انتخاب کنید", "th": "เลือกเวลา"
};

NOEL_I18N["form.choose_date"] = {
  "en": "Choose a date", "es": "Elige una fecha", "fr": "Choisissez une date", "ar": "اختر تاريخًا",
  "pt": "Escolha uma data", "ur": "Date chunen", "hi": "तारीख़ चुनें", "bn": "তারিখ বেছে নিন",
  "ud": "تاریخ منتخب کریں", "zh": "选择日期", "de": "Datum wählen", "it": "Scegli una data",
  "ru": "Выберите дату", "tr": "Bir tarih seçin", "ko": "날짜 선택", "ja": "日付を選択",
  "vi": "Chọn ngày", "fa": "تاریخ را انتخاب کنید", "th": "เลือกวันที่"
};

NOEL_I18N["form.phone_ph"] = {
  "en": "Your phone number", "es": "Tu número de teléfono", "fr": "Votre numéro de téléphone", "ar": "رقم هاتفك",
  "pt": "Seu número de telefone", "ur": "Aapka phone number", "hi": "आपका फ़ोन नंबर", "bn": "আপনার ফোন নম্বর",
  "ud": "آپ کا فون نمبر", "zh": "您的电话号码", "de": "Ihre Telefonnummer", "it": "Il tuo numero di telefono",
  "ru": "Ваш номер телефона", "tr": "Telefon numaranız", "ko": "전화번호", "ja": "お客様の電話番号",
  "vi": "Số điện thoại của bạn", "fa": "شماره تلفن شما", "th": "หมายเลขโทรศัพท์ของคุณ"
};

NOEL_I18N["form.flight_ph_short"] = {
  "en": "e.g. EK215", "es": "p. ej., EK215", "fr": "p. ex. EK215", "ar": "مثال: EK215",
  "pt": "ex.: EK215", "ur": "e.g. EK215", "hi": "जैसे EK215", "bn": "যেমন EK215",
  "ud": "جیسے EK215", "zh": "例如 EK215", "de": "z. B. EK215", "it": "es. EK215",
  "ru": "напр., EK215", "tr": "ör. EK215", "ko": "예: EK215", "ja": "例：EK215",
  "vi": "vd: EK215", "fa": "مثل EK215", "th": "เช่น EK215"
};

NOEL_I18N["form.back_to_form"] = {
  "en": "← Back to booking form", "es": "← Volver al formulario de reserva", "fr": "← Retour au formulaire de réservation", "ar": "← العودة إلى نموذج الحجز",
  "pt": "← Voltar ao formulário de reserva", "ur": "← Booking form par wapas", "hi": "← बुकिंग फ़ॉर्म पर वापस जाएँ", "bn": "← বুকিং ফর্মে ফিরে যান",
  "ud": "← بکنگ فارم پر واپس جائیں", "zh": "← 返回预订表格", "de": "← Zurück zum Buchungsformular", "it": "← Torna al modulo di prenotazione",
  "ru": "← Назад к форме бронирования", "tr": "← Rezervasyon formuna geri dön", "ko": "← 예약 양식으로 돌아가기", "ja": "← 予約フォームに戻る",
  "vi": "← Quay lại biểu mẫu đặt xe", "fa": "← بازگشت به فرم رزرو", "th": "← กลับไปที่แบบฟอร์มการจอง"
};

NOEL_I18N["form.pay"] = {
  "en": "Pay", "es": "Pagar", "fr": "Payer", "ar": "ادفع",
  "pt": "Pagar", "ur": "Pay karen", "hi": "भुगतान करें", "bn": "পেমেন্ট করুন",
  "ud": "ادائیگی کریں", "zh": "支付", "de": "Bezahlen", "it": "Paga",
  "ru": "Оплатить", "tr": "Öde", "ko": "결제", "ja": "支払う",
  "vi": "Thanh toán", "fa": "پرداخت", "th": "ชำระเงิน"
};

NOEL_I18N["hourly.miles_note"] = {
  "en": "Includes {total} miles of travel ({per_hour} miles per hour) — taxes and tolls included.", "es": "Incluye {total} millas de viaje ({per_hour} millas por hora); impuestos y peajes incluidos.", "fr": "Comprend {total} miles de trajet ({per_hour} miles par heure) — taxes et péages inclus.", "ar": "يشمل {total} ميلًا من السفر ({per_hour} ميلًا في الساعة) — الضرائب والرسوم مشمولة.",
  "pt": "Inclui {total} milhas de viagem ({per_hour} milhas por hora) — impostos e pedágios incluídos.", "ur": "{total} miles travel shamil hai ({per_hour} miles per hour) — taxes aur tolls shamil hain.", "hi": "{total} मील की यात्रा शामिल है (प्रति घंटे {per_hour} मील) — कर और टोल शामिल हैं।", "bn": "{total} মাইল ভ্রমণ অন্তর্ভুক্ত (প্রতি ঘণ্টায় {per_hour} মাইল) — কর ও টোল অন্তর্ভুক্ত।",
  "ud": "{total} میل شامل ہیں ({per_hour} میل فی گھنٹہ) — ٹیکس اور ٹول شامل ہیں", "zh": "包含 {total} 英里行程（每小时 {per_hour} 英里）——税费和过路费已包含。", "de": "Inklusive {total} Meilen Fahrt ({per_hour} Meilen pro Stunde) — Steuern und Maut inklusive.", "it": "Include {total} miglia di viaggio ({per_hour} miglia all'ora) — tasse e pedaggi inclusi.",
  "ru": "Включает {total} миль поездки ({per_hour} миль в час) — налоги и сборы включены.", "tr": "{total} mil yolculuk dahildir (saat başına {per_hour} mil) — vergiler ve geçiş ücretleri dahildir.", "ko": "{total}마일 이동 포함(시간당 {per_hour}마일) — 세금 및 통행료 포함.", "ja": "{total}マイルの走行を含む（1時間あたり{per_hour}マイル）— 税金と通行料込み。",
  "vi": "Bao gồm {total} dặm di chuyển ({per_hour} dặm mỗi giờ) — đã bao gồm thuế và phí cầu đường.", "fa": "{total} مایل شامل است ({per_hour} مایل در ساعت) — مالیات و عوارض شامل است", "th": "รวมระยะทาง {total} ไมล์ ({per_hour} ไมล์ต่อชั่วโมง) — รวมภาษีและค่าผ่านทางแล้ว"
};

NOEL_I18N["status.booking_cancelled_heading"] = {
  "en": "Booking cancelled", "es": "Reserva cancelada", "fr": "Réservation annulée", "ar": "تم إلغاء الحجز",
  "pt": "Reserva cancelada", "ur": "Booking cancel ho gayi", "hi": "बुकिंग रद्द कर दी गई", "bn": "বুকিং বাতিল করা হয়েছে",
  "ud": "بکنگ منسوخ کر دی گئی", "zh": "预订已取消", "de": "Buchung storniert", "it": "Prenotazione annullata",
  "ru": "Бронирование отменено", "tr": "Rezervasyon iptal edildi", "ko": "예약 취소됨", "ja": "予約がキャンセルされました",
  "vi": "Đã hủy đặt xe", "fa": "رزرو لغو شد", "th": "ยกเลิกการจองแล้ว"
};

NOEL_I18N["status.flight_label"] = {
  "en": "Flight", "es": "Vuelo", "fr": "Vol", "ar": "الرحلة",
  "pt": "Voo", "ur": "Flight", "hi": "फ़्लाइट", "bn": "ফ্লাইট",
  "ud": "فلائٹ", "zh": "航班", "de": "Flug", "it": "Volo",
  "ru": "Рейс", "tr": "Uçuş", "ko": "항공편", "ja": "便",
  "vi": "Chuyến bay", "fa": "پرواز", "th": "เที่ยวบิน"
};

NOEL_I18N["form.pickup"] = {
  "en": "Pickup address", "es": "Dirección de recogida", "fr": "Adresse de prise en charge", "ar": "عنوان الاستلام",
  "pt": "Endereço de embarque", "ur": "Pickup address", "hi": "पिकअप का पता", "bn": "পিকআপের ঠিকানা",
  "ud": "پک اپ کا پتہ", "zh": "上车地址", "de": "Abholadresse", "it": "Indirizzo di partenza",
  "ru": "Адрес отправления", "tr": "Biniş adresi", "ko": "출발지 주소", "ja": "出発地の住所",
  "vi": "Địa chỉ đón", "fa": "نشانی مبدا", "th": "ที่อยู่ต้นทาง"
};

NOEL_I18N["form.pickup_ph"] = {
  "en": "Where from?", "es": "¿Desde dónde?", "fr": "D'où partez-vous ?", "ar": "من أين؟",
  "pt": "De onde?", "ur": "Kahan se?", "hi": "कहाँ से?", "bn": "কোথা থেকে?",
  "ud": "کہاں سے؟", "zh": "从哪里出发？", "de": "Woher?", "it": "Da dove?",
  "ru": "Откуда?", "tr": "Nereden?", "ko": "어디에서 출발하시나요?", "ja": "どこから？",
  "vi": "Đón ở đâu?", "fa": "از کجا؟", "th": "จากที่ไหน?"
};

NOEL_I18N["form.dropoff"] = {
  "en": "Drop-off address", "es": "Dirección de destino", "fr": "Adresse de destination", "ar": "عنوان الوصول",
  "pt": "Endereço de destino", "ur": "Drop-off address", "hi": "ड्रॉप-ऑफ़ का पता", "bn": "ড্রপ-অফের ঠিকানা",
  "ud": "ڈراپ آف کا پتہ", "zh": "下车地址", "de": "Zieladresse", "it": "Indirizzo di destinazione",
  "ru": "Адрес назначения", "tr": "Varış adresi", "ko": "목적지 주소", "ja": "目的地の住所",
  "vi": "Địa chỉ trả khách", "fa": "نشانی مقصد", "th": "ที่อยู่ปลายทาง"
};

NOEL_I18N["form.dropoff_ph"] = {
  "en": "Where to?", "es": "¿Adónde?", "fr": "Où allez-vous ?", "ar": "إلى أين؟",
  "pt": "Para onde?", "ur": "Kahan tak?", "hi": "कहाँ तक?", "bn": "কোথায় যাবেন?",
  "ud": "کہاں جانا ہے؟", "zh": "去哪里？", "de": "Wohin?", "it": "Dove?",
  "ru": "Куда?", "tr": "Nereye?", "ko": "어디로 가시나요?", "ja": "どこへ？",
  "vi": "Đi đâu?", "fa": "به کجا؟", "th": "ไปที่ไหน?"
};

NOEL_I18N["form.date"] = {
  "en": "Date", "es": "Fecha", "fr": "Date", "ar": "التاريخ",
  "pt": "Data", "ur": "Date", "hi": "तारीख", "bn": "তারিখ",
  "ud": "تاریخ", "zh": "日期", "de": "Datum", "it": "Data",
  "ru": "Дата", "tr": "Tarih", "ko": "날짜", "ja": "日付",
  "vi": "Ngày", "fa": "تاریخ", "th": "วันที่"
};

NOEL_I18N["form.pickup_time"] = {
  "en": "Pickup time", "es": "Hora de recogida", "fr": "Heure de prise en charge", "ar": "وقت الاستلام",
  "pt": "Hora de embarque", "ur": "Pickup time", "hi": "पिकअप का समय", "bn": "পিকআপের সময়",
  "ud": "پک اپ کا وقت", "zh": "上车时间", "de": "Abholzeit", "it": "Ora di ritiro",
  "ru": "Время подачи", "tr": "Biniş saati", "ko": "픽업 시간", "ja": "乗車時刻",
  "vi": "Giờ đón", "fa": "زمان سوارشدن", "th": "เวลารับ"
};

NOEL_I18N["form.flight_number"] = {
  "en": "Flight number", "es": "Número de vuelo", "fr": "Numéro de vol", "ar": "رقم الرحلة",
  "pt": "Número do voo", "ur": "Flight number", "hi": "फ़्लाइट नंबर", "bn": "ফ্লাইট নম্বর",
  "ud": "فلائٹ نمبر", "zh": "航班号", "de": "Flugnummer", "it": "Numero di volo",
  "ru": "Номер рейса", "tr": "Uçuş numarası", "ko": "항공편 번호", "ja": "便名",
  "vi": "Số hiệu chuyến bay", "fa": "شمارهٔ پرواز", "th": "หมายเลขเที่ยวบิน"
};

NOEL_I18N["form.flight_ph"] = {
  "en": "e.g. LH202, BA2490", "es": "p. ej., LH202, BA2490", "fr": "p. ex. LH202, BA2490", "ar": "مثال: LH202, BA2490",
  "pt": "ex.: LH202, BA2490", "ur": "e.g. LH202, BA2490", "hi": "जैसे LH202, BA2490", "bn": "যেমন LH202, BA2490",
  "ud": "جیسے LH202, BA2490", "zh": "例如 LH202、BA2490", "de": "z. B. LH202, BA2490", "it": "es. LH202, BA2490",
  "ru": "напр., LH202, BA2490", "tr": "ör. LH202, BA2490", "ko": "예: LH202, BA2490", "ja": "例：LH202、BA2490",
  "vi": "vd: LH202, BA2490", "fa": "مثل LH202, BA2490", "th": "เช่น LH202, BA2490"
};

NOEL_I18N["form.hours"] = {
  "en": "Hours", "es": "Horas", "fr": "Heures", "ar": "الساعات",
  "pt": "Horas", "ur": "Hours", "hi": "घंटे", "bn": "ঘণ্টা",
  "ud": "گھنٹے", "zh": "小时", "de": "Stunden", "it": "Ore",
  "ru": "Часы", "tr": "Saat", "ko": "시간", "ja": "時間",
  "vi": "Giờ", "fa": "ساعت", "th": "ชั่วโมง"
};

NOEL_I18N["form.hours_hint"] = {
  "en": "Minimum 2 hours, maximum 24. Your chauffeur stays with you for the hours you book.", "es": "Mínimo 2 horas, máximo 24. Tu chófer se queda contigo durante las horas reservadas.", "fr": "Minimum 2 heures, maximum 24. Votre chauffeur reste avec vous pendant les heures réservées.", "ar": "الحد الأدنى ساعتان، والحد الأقصى 24 ساعة. يبقى سائقك معك طوال الساعات التي تحجزها.",
  "pt": "Mínimo de 2 horas, máximo de 24. Seu motorista fica com você durante as horas reservadas.", "ur": "Kam se kam 2 hours, zyada se zyada 24. Aapka chauffeur utni der aapke saath rahega jitne hours aap book karenge.", "hi": "कम से कम 2 घंटे, अधिकतम 24। आपका शॉफ़र उतने समय तक आपके साथ रहेगा जितने घंटे आप बुक करेंगे।", "bn": "সর্বনিম্ন ২ ঘণ্টা, সর্বোচ্চ ২৪। আপনার শোফার যত ঘণ্টা বুক করবেন ততক্ষণ আপনার সঙ্গে থাকবেন।",
  "ud": "کم از کم 2 گھنٹے، زیادہ سے زیادہ 24 گھنٹے۔ آپ کا ڈرائیور بک کیے گئے تمام گھنٹوں کے لیے آپ کے ساتھ رہے گا", "zh": "最少2小时，最多24小时。在您预订的时间内司机将一直陪伴您。", "de": "Mindestens 2 Stunden, maximal 24. Ihr Chauffeur bleibt für die von Ihnen gebuchten Stunden bei Ihnen.", "it": "Minimo 2 ore, massimo 24. Il tuo chauffeur resta con te per le ore prenotate.",
  "ru": "Минимум 2 часа, максимум 24. Ваш шофёр останется с вами на забронированные часы.", "tr": "En az 2 saat, en fazla 24 saat. Şoförünüz rezerve ettiğiniz saatler boyunca sizinle kalır.", "ko": "최소 2시간, 최대 24시간. 예약한 시간 동안 쇼퍼가 함께합니다.", "ja": "最低2時間、最大24時間。予約した時間、ショファーがお客様と一緒にいます。",
  "vi": "Tối thiểu 2 giờ, tối đa 24 giờ. Tài xế của bạn sẽ ở cùng bạn trong số giờ bạn đặt.", "fa": "حداقل ۲ ساعت، حداکثر ۲۴ ساعت. رانندهٔ شما در تمام ساعت‌های رزروشده نزد شما می‌ماند", "th": "ขั้นต่ำ 2 ชั่วโมง สูงสุด 24 ชั่วโมง คนขับของคุณจะอยู่กับคุณตลอดชั่วโมงที่จอง"
};

NOEL_I18N["form.view_options"] = {
  "en": "View options", "es": "Ver opciones", "fr": "Voir les options", "ar": "عرض الخيارات",
  "pt": "Ver opções", "ur": "Options dekhen", "hi": "विकल्प देखें", "bn": "বিকল্প দেখুন",
  "ud": "اختیارات دیکھیں", "zh": "查看选项", "de": "Optionen ansehen", "it": "Vedi opzioni",
  "ru": "Посмотреть варианты", "tr": "Seçenekleri görüntüle", "ko": "옵션 보기", "ja": "オプションを見る",
  "vi": "Xem các lựa chọn", "fa": "مشاهدهٔ گزینه‌ها", "th": "ดูตัวเลือก"
};

NOEL_I18N["form.required"] = {
  "en": "This field is required", "es": "Este campo es obligatorio", "fr": "Ce champ est obligatoire", "ar": "هذا الحقل مطلوب",
  "pt": "Este campo é obrigatório", "ur": "Ye field zaroori hai", "hi": "यह फ़ील्ड ज़रूरी है", "bn": "এই ঘরটি পূরণ করা আবশ্যক",
  "ud": "یہ فیلڈ درکار ہے", "zh": "此字段为必填项", "de": "Dieses Feld ist erforderlich", "it": "Questo campo è obbligatorio",
  "ru": "Это поле обязательно", "tr": "Bu alan zorunludur", "ko": "필수 입력 항목입니다", "ja": "この項目は必須です",
  "vi": "Trường này là bắt buộc", "fa": "این فیلد الزامی است", "th": "ต้องกรอกช่องนี้"
};

NOEL_I18N["form.sending"] = {
  "en": "Sending your request…", "es": "Enviando tu solicitud…", "fr": "Envoi de votre demande…", "ar": "جارٍ إرسال طلبك…",
  "pt": "Enviando sua solicitação…", "ur": "Aapki request bheji ja rahi hai…", "hi": "आपका अनुरोध भेजा जा रहा है…", "bn": "আপনার অনুরোধ পাঠানো হচ্ছে…",
  "ud": "آپ کی درخواست بھیجی جا رہی ہے…", "zh": "正在发送您的请求…", "de": "Ihre Anfrage wird gesendet…", "it": "Invio della richiesta…",
  "ru": "Отправка вашего запроса…", "tr": "İsteğiniz gönderiliyor…", "ko": "요청을 보내는 중…", "ja": "リクエストを送信中…",
  "vi": "Đang gửi yêu cầu của bạn…", "fa": "در حال ارسال درخواست شما…", "th": "กำลังส่งคำขอของคุณ…"
};

NOEL_I18N["form.paused"] = {
  "en": "Bookings are paused while we update our prices. Please check back soon.", "es": "Las reservas están en pausa mientras actualizamos nuestros precios. Vuelve pronto.", "fr": "Les réservations sont suspendues pendant la mise à jour de nos tarifs. Revenez bientôt.", "ar": "الحجوزات متوقفة مؤقتًا أثناء تحديث أسعارنا. يرجى العودة قريبًا.",
  "pt": "As reservas estão pausadas enquanto atualizamos nossos preços. Volte em breve.", "ur": "Prices update ho rahe hain is liye bookings ruki hui hain. Thodi der mein phir check karen.", "hi": "हमारे दाम अपडेट हो रहे हैं, इसलिए बुकिंग रुकी हुई है। कृपया थोड़ी देर में फिर देखें।", "bn": "আমাদের দাম আপডেট হচ্ছে বলে বুকিং সাময়িক বন্ধ আছে। শীঘ্রই আবার দেখুন।",
  "ud": "قیمتوں کو اپ ڈیٹ کرتے وقت بکنگ عارضی طور پر رکی ہوئی ہے، براہ کرم جلد دوبارہ چیک کریں", "zh": "我们正在更新价格，预订已暂停。请稍后再查看。", "de": "Buchungen sind pausiert, während wir unsere Preise aktualisieren. Bitte schauen Sie bald wieder vorbei.", "it": "Le prenotazioni sono in pausa mentre aggiorniamo i nostri prezzi. Torna a trovarci presto.",
  "ru": "Бронирование приостановлено, пока мы обновляем наши цены. Пожалуйста, зайдите позже.", "tr": "Fiyatlarımızı güncellerken rezervasyonlar duraklatıldı. Lütfen yakında tekrar kontrol edin.", "ko": "가격 업데이트 중 예약이 중단되었습니다. 곧 다시 확인해 주세요.", "ja": "料金更新のため、予約を一時停止しています。しばらくしてから再度ご確認ください。",
  "vi": "Đặt xe đang tạm dừng trong khi chúng tôi cập nhật giá. Vui lòng kiểm tra lại sớm.", "fa": "رزرو در حین به‌روزرسانی قیمت‌ها موقتاً متوقف است، لطفاً به‌زودی دوباره بررسی کنید", "th": "การจองหยุดชั่วคราวในขณะที่เราปรับปรุงราคา โปรดกลับมาตรวจสอบอีกครั้งเร็วๆ นี้"
};

NOEL_I18N["form.hourly_need"] = {
  "en": "Hourly bookings need 2 to 24 hours.", "es": "Las reservas por horas necesitan de 2 a 24 horas.", "fr": "Les réservations à l'heure nécessitent de 2 à 24 heures.", "ar": "الحجز بالساعة يحتاج من ساعتين إلى 24 ساعة.",
  "pt": "Reservas por hora precisam de 2 a 24 horas.", "ur": "Hourly booking ke liye 2 se 24 hours chahiye.", "hi": "घंटे वाली बुकिंग के लिए 2 से 24 घंटे चाहिए।", "bn": "ঘণ্টা হিসেবে বুকিংয়ের জন্য ২ থেকে ২৪ ঘণ্টা লাগবে।",
  "ud": "فی گھنٹہ بکنگ کے لیے 2 سے 24 گھنٹے درکار ہیں", "zh": "按小时预订需要2至24小时。", "de": "Stundenweise Buchungen erfordern 2 bis 24 Stunden.", "it": "Le prenotazioni a ore richiedono da 2 a 24 ore.",
  "ru": "Почасовое бронирование требует от 2 до 24 часов.", "tr": "Saatlik rezervasyonlar 2 ila 24 saat gerektirir.", "ko": "시간제 예약은 2~24시간이 필요합니다.", "ja": "時間貸しの予約には2〜24時間が必要です。",
  "vi": "Đặt xe theo giờ cần 2 đến 24 giờ.", "fa": "رزرو ساعتی به ۲ تا ۲۴ ساعت نیاز دارد", "th": "การจองรายชั่วโมงต้องใช้ 2 ถึง 24 ชั่วโมง"
};

NOEL_I18N["form.choose_datetime"] = {
  "en": "Please choose a date and time.", "es": "Elige una fecha y una hora.", "fr": "Veuillez choisir une date et une heure.", "ar": "يرجى اختيار التاريخ والوقت.",
  "pt": "Escolha uma data e uma hora.", "ur": "Date aur time chunen.", "hi": "कृपया तारीख और समय चुनें।", "bn": "দয়া করে তারিখ ও সময় বেছে নিন।",
  "ud": "براہ کرم تاریخ اور وقت منتخب کریں", "zh": "请选择日期和时间。", "de": "Bitte wählen Sie Datum und Uhrzeit.", "it": "Scegli data e ora.",
  "ru": "Пожалуйста, выберите дату и время.", "tr": "Lütfen bir tarih ve saat seçin.", "ko": "날짜와 시간을 선택해 주세요.", "ja": "日付と時刻を選択してください。",
  "vi": "Vui lòng chọn ngày và giờ.", "fa": "لطفاً تاریخ و زمان را انتخاب کنید", "th": "โปรดเลือกวันที่และเวลา"
};

NOEL_I18N["form.past_date"] = {
  "en": "Please choose a date from today onwards. Past dates cannot be booked.", "es": "Elige una fecha a partir de hoy. No se pueden reservar fechas pasadas.", "fr": "Veuillez choisir une date à partir d'aujourd'hui. Les dates passées ne peuvent pas être réservées.", "ar": "يرجى اختيار تاريخ من اليوم فصاعدًا. لا يمكن حجز التواريخ الماضية.",
  "pt": "Escolha uma data a partir de hoje. Datas passadas não podem ser reservadas.", "ur": "Aaj se aage ki date chunen. Beeti hui date book nahi ho sakti.", "hi": "कृपया आज से आगे की तारीख चुनें। बीती तारीख बुक नहीं हो सकती।", "bn": "দয়া করে আজ থেকে পরের কোনো তারিখ বেছে নিন। আগের তারিখ বুক করা যাবে না।",
  "ud": "براہ کرم آج سے شروع ہونے والی تاریخ منتخب کریں، گزری ہوئی تاریخ بک نہیں کی جا سکتی", "zh": "请选择今天或之后的日期。过去的日期无法预订。", "de": "Bitte wählen Sie ein Datum ab heute. Vergangene Daten können nicht gebucht werden.", "it": "Scegli una data da oggi in poi. Non è possibile prenotare date passate.",
  "ru": "Пожалуйста, выберите дату начиная с сегодняшнего дня. Прошедшие даты забронировать нельзя.", "tr": "Lütfen bugünden itibaren bir tarih seçin. Geçmiş tarihler rezerve edilemez.", "ko": "오늘 이후의 날짜를 선택해 주세요. 지난 날짜는 예약할 수 없습니다.", "ja": "今日以降の日付を選択してください。過去の日付は予約できません。",
  "vi": "Vui lòng chọn ngày từ hôm nay trở đi. Không thể đặt ngày trong quá khứ.", "fa": "لطفاً تاریخی از امروز به بعد انتخاب کنید، تاریخ گذشته را نمی‌توان رزرو کرد", "th": "โปรดเลือกวันที่ตั้งแต่วันนี้เป็นต้นไป ไม่สามารถจองวันที่ผ่านมาแล้วได้"
};

NOEL_I18N["form.past_time"] = {
  "en": "Please choose a time later than now. Past times cannot be booked.", "es": "Elige una hora posterior a la actual. No se pueden reservar horas pasadas.", "fr": "Veuillez choisir une heure ultérieure. Les heures passées ne peuvent pas être réservées.", "ar": "يرجى اختيار وقت لاحق للوقت الحالي. لا يمكن حجز الأوقات الماضية.",
  "pt": "Escolha um horário posterior ao atual. Horários passados não podem ser reservados.", "ur": "Ab se baad ka time chunen. Beeta hua time book nahi ho sakta.", "hi": "कृपया अभी से बाद का समय चुनें। बीता समय बुक नहीं हो सकता।", "bn": "দয়া করে এখনকার চেয়ে পরের সময় বেছে নিন। আগের সময় বুক করা যাবে না।",
  "ud": "براہ کرم اب سے بعد کا وقت منتخب کریں، گزرا ہوا وقت بک نہیں کیا جا سکتا", "zh": "请选择比现在更晚的时间。过去的时间无法预订。", "de": "Bitte wählen Sie eine spätere Uhrzeit. Vergangene Uhrzeiten können nicht gebucht werden.", "it": "Scegli un orario successivo a ora. Non è possibile prenotare orari passati.",
  "ru": "Пожалуйста, выберите время позже текущего. Прошедшее время забронировать нельзя.", "tr": "Lütfen şimdiden daha ileri bir saat seçin. Geçmiş saatler rezerve edilemez.", "ko": "현재보다 늦은 시간을 선택해 주세요. 지난 시간은 예약할 수 없습니다.", "ja": "現在より後の時刻を選択してください。過去の時刻は予約できません。",
  "vi": "Vui lòng chọn thời gian muộn hơn bây giờ. Không thể đặt thời gian trong quá khứ.", "fa": "لطفاً زمانی دیرتر از اکنون انتخاب کنید، زمان گذشته را نمی‌توان رزرو کرد", "th": "โปรดเลือกเวลาที่ช้ากว่าตอนนี้ ไม่สามารถจองเวลาที่ผ่านมาแล้วได้"
};

NOEL_I18N["form.fill_details"] = {
  "en": "Please fill in your name, phone and email.", "es": "Completa tu nombre, teléfono y correo electrónico.", "fr": "Veuillez renseigner votre nom, votre téléphone et votre e-mail.", "ar": "يرجى إدخال اسمك ورقم هاتفك وبريدك الإلكتروني.",
  "pt": "Preencha seu nome, telefone e e-mail.", "ur": "Apna naam, phone aur email likhen.", "hi": "कृपया अपना नाम, फ़ोन और ईमेल भरें।", "bn": "দয়া করে আপনার নাম, ফোন ও ইমেইল লিখুন।",
  "ud": "براہ کرم اپنا نام، فون اور ای میل درج کریں", "zh": "请填写您的姓名、电话和邮箱。", "de": "Bitte geben Sie Ihren Namen, Ihre Telefonnummer und Ihre E-Mail-Adresse ein.", "it": "Inserisci nome, telefono ed email.",
  "ru": "Пожалуйста, введите ваше имя, телефон и электронную почту.", "tr": "Lütfen adınızı, telefonunuzu ve e-postanızı girin.", "ko": "이름, 전화번호, 이메일을 입력해 주세요.", "ja": "お名前、電話番号、メールアドレスを入力してください。",
  "vi": "Vui lòng điền tên, số điện thoại và email của bạn.", "fa": "لطفاً نام، تلفن و ایمیل خود را وارد کنید", "th": "โปรดกรอกชื่อ โทรศัพท์ และอีเมลของคุณ"
};

NOEL_I18N["form.continue"] = {
  "en": "Continue", "es": "Continuar", "fr": "Continuer", "ar": "متابعة",
  "pt": "Continuar", "ur": "Continue", "hi": "जारी रखें", "bn": "চালিয়ে যান",
  "ud": "جاری رکھیں", "zh": "继续", "de": "Weiter", "it": "Continua",
  "ru": "Продолжить", "tr": "Devam", "ko": "계속", "ja": "続ける",
  "vi": "Tiếp tục", "fa": "ادامه", "th": "ดำเนินการต่อ"
};

NOEL_I18N["form.skip"] = {
  "en": "Skip", "es": "Omitir", "fr": "Passer", "ar": "تخطَّ",
  "pt": "Pular", "ur": "Skip karen", "hi": "छोड़ें", "bn": "এড়িয়ে যান",
  "ud": "چھوڑیں", "zh": "跳过", "de": "Überspringen", "it": "Salta",
  "ru": "Пропустить", "tr": "Atla", "ko": "건너뛰기", "ja": "スキップ",
  "vi": "Bỏ qua", "fa": "رد کردن", "th": "ข้าม"
};

NOEL_I18N["form.flight_title"] = {
  "en": "Add your flight number", "es": "Añade tu número de vuelo", "fr": "Ajoutez votre numéro de vol", "ar": "أضف رقم رحلتك",
  "pt": "Adicione o número do seu voo", "ur": "Apni flight number likhen", "hi": "अपनी फ़्लाइट संख्या जोड़ें", "bn": "আপনার ফ্লাইট নম্বর যোগ করুন",
  "ud": "اپنا فلائٹ نمبر شامل کریں", "zh": "添加您的航班号", "de": "Flugnummer hinzufügen", "it": "Aggiungi il numero di volo",
  "ru": "Добавить номер рейса", "tr": "Uçuş numaranızı ekleyin", "ko": "항공편 번호 추가", "ja": "便名を追加",
  "vi": "Thêm số hiệu chuyến bay của bạn", "fa": "شمارهٔ پرواز خود را اضافه کنید", "th": "เพิ่มหมายเลขเที่ยวบินของคุณ"
};

NOEL_I18N["form.flight_title_opt"] = {
  "en": "Add your flight number (optional)", "es": "Añade tu número de vuelo (opcional)", "fr": "Ajoutez votre numéro de vol (facultatif)", "ar": "أضف رقم رحلتك (اختياري)",
  "pt": "Adicione o número do seu voo (opcional)", "ur": "Apni flight number likhen (optional)", "hi": "अपनी फ़्लाइट संख्या जोड़ें (वैकल्पिक)", "bn": "আপনার ফ্লাইট নম্বর যোগ করুন (ঐচ্ছিক)",
  "ud": "اپنا فلائٹ نمبر شامل کریں (اختیاری)", "zh": "添加您的航班号（可选）", "de": "Flugnummer hinzufügen (optional)", "it": "Aggiungi il numero di volo (facoltativo)",
  "ru": "Добавить номер рейса (необязательно)", "tr": "Uçuş numaranızı ekleyin (isteğe bağlı)", "ko": "항공편 번호 추가(선택 사항)", "ja": "便名を追加（任意）",
  "vi": "Thêm số hiệu chuyến bay của bạn (tùy chọn)", "fa": "شمارهٔ پرواز خود را اضافه کنید (اختیاری)", "th": "เพิ่มหมายเลขเที่ยวบินของคุณ (ไม่บังคับ)"
};

NOEL_I18N["form.flight_text_pickup"] = {
  "en": "Your chauffeur will meet you at the right terminal.", "es": "Tu chófer te esperará en la terminal correcta.", "fr": "Votre chauffeur vous attendra au bon terminal.", "ar": "سيقابلك سائقك في الصالة الصحيحة.",
  "pt": "Seu motorista encontrará você no terminal certo.", "ur": "Aapka chauffeur sahi terminal par aapko milega.", "hi": "आपका शॉफ़र सही टर्मिनल पर आपसे मिलेगा।", "bn": "আপনার শোফার সঠিক টার্মিনালে আপনার সঙ্গে দেখা করবেন।",
  "ud": "آپ کا ڈرائیور آپ سے صحیح ٹرمینل پر ملے گا", "zh": "您的司机将在正确的航站楼迎接您。", "de": "Ihr Chauffeur erwartet Sie am richtigen Terminal.", "it": "Il tuo chauffeur ti incontrerà al terminal giusto.",
  "ru": "Ваш шофёр встретит вас у нужного терминала.", "tr": "Şoförünüz sizi doğru terminalde karşılayacak.", "ko": "쇼퍼가 올바른 터미널에서 맞이합니다.", "ja": "ショファーが正しいターミナルでお迎えします。",
  "vi": "Tài xế của bạn sẽ gặp bạn tại nhà ga đúng.", "fa": "رانندهٔ شما در ترمینال صحیح با شما ملاقات می‌کند", "th": "คนขับของคุณจะพบคุณที่อาคารผู้โดยสารที่ถูกต้อง"
};

NOEL_I18N["form.flight_text_dropoff"] = {
  "en": "This helps your chauffeur take you to the right departure terminal.", "es": "Esto ayuda a tu chófer a llevarte a la terminal de salida correcta.", "fr": "Cela aide votre chauffeur à vous conduire au bon terminal de départ.", "ar": "يساعد هذا سائقك على إيصالك إلى صالة المغادرة الصحيحة.",
  "pt": "Isso ajuda seu motorista a levá-lo ao terminal de embarque certo.", "ur": "Is se aapka chauffeur aapko sahi departure terminal tak le jayega.", "hi": "इससे आपका शॉफ़र आपको सही प्रस्थान टर्मिनल तक ले जाएगा।", "bn": "এতে আপনার শোফার আপনাকে সঠিক যাত্রা টার্মিনালে নিয়ে যেতে পারবেন।",
  "ud": "اس سے ڈرائیور کو آپ کو صحیح روانگی ٹرمینل تک پہنچانے میں مدد ملتی ہے", "zh": "这有助于您的司机将您送到正确的出发航站楼。", "de": "So bringt Ihr Chauffeur Sie zum richtigen Abflugterminal.", "it": "Questo aiuta il tuo chauffeur a portarti al terminal di partenza giusto.",
  "ru": "Это поможет вашему шофёру отвезти вас к нужному терминалу вылета.", "tr": "Bu, şoförünüzün sizi doğru kalkış terminaline götürmesine yardımcı olur.", "ko": "쇼퍼가 올바른 출발 터미널로 모셔다 드리는 데 도움이 됩니다.", "ja": "ショファーが正しい出発ターミナルへお連れするのに役立ちます。",
  "vi": "Điều này giúp tài xế đưa bạn đến nhà ga khởi hành đúng.", "fa": "این به راننده کمک می‌کند شما را به ترمینال خروج صحیح برساند", "th": "สิ่งนี้ช่วยให้คนขับพาคุณไปยังอาคารผู้โดยสารขาออกที่ถูกต้อง"
};

NOEL_I18N["form.flight_skip_note"] = {
  "en": "You can skip this — your booking will still go through.", "es": "Puedes omitir esto: tu reserva seguirá adelante.", "fr": "Vous pouvez passer cette étape — votre réservation sera quand même confirmée.", "ar": "يمكنك تخطي هذه الخطوة — وسيتم حجزك على أي حال.",
  "pt": "Você pode pular esta etapa — sua reserva seguirá normalmente.", "ur": "Aap ye skip kar sakte hain — aapki booking phir bhi ho jayegi.", "hi": "आप इसे छोड़ सकते हैं — आपकी बुकिंग फिर भी हो जाएगी।", "bn": "আপনি এটা এড়িয়ে যেতে পারেন — আপনার বুকিং তবুও হয়ে যাবে।",
  "ud": "آپ اسے چھوڑ سکتے ہیں — آپ کی بکنگ پھر بھی جاری رہے گی", "zh": "您可以跳过这一步——您的预订仍会完成。", "de": "Sie können dies überspringen — Ihre Buchung wird trotzdem bearbeitet.", "it": "Puoi saltare questo passaggio — la prenotazione andrà comunque a buon fine.",
  "ru": "Вы можете пропустить это — ваше бронирование всё равно будет оформлено.", "tr": "Bunu atlayabilirsiniz — rezervasyonunuz yine de tamamlanır.", "ko": "건너뛰어도 됩니다. 예약은 그대로 진행됩니다.", "ja": "スキップできます。予約はそのまま進みます。",
  "vi": "Bạn có thể bỏ qua bước này — đặt xe của bạn vẫn sẽ được xử lý.", "fa": "می‌توانید این را رد کنید — رزرو شما همچنان ادامه می‌یابد", "th": "คุณสามารถข้ามขั้นตอนนี้ได้ — การจองของคุณจะยังคงดำเนินการ"
};

NOEL_I18N["class.ny_congestion"] = {
  "en": "NY State congestion surcharge", "es": "Recargo por congestión del estado de Nueva York", "fr": "Supplément de congestion de l'État de New York", "ar": "رسوم ازدحام ولاية نيويورك",
  "pt": "Sobretaxa de congestionamento do estado de Nova York", "ur": "NY State congestion surcharge", "hi": "न्यूयॉर्क राज्य भीड़ अधिभार", "bn": "নিউ ইয়র্ক স্টেট যানজট সারচার্জ",
  "ud": "نیویارک کنجیشن فیس", "zh": "纽约州拥堵附加费", "de": "Stauzuschlag des Staates New York", "it": "Supplemento di congestione dello Stato di New York",
  "ru": "Надбавка штата Нью-Йорк за пробки", "tr": "New York Eyaleti trafik yoğunluğu ek ücreti", "ko": "뉴욕주 혼잡 통행료", "ja": "ニューヨーク州渋滞追加料金",
  "vi": "Phụ phí tắc nghẽn của Bang New York", "fa": "هزینهٔ ازدحام نیویورک", "th": "ค่าธรรมเนียมจราจรหนาแน่นของรัฐนิวยอร์ก"
};

NOEL_I18N["class.mta_congestion"] = {
  "en": "MTA congestion surcharge", "es": "Recargo por congestión de la MTA", "fr": "Supplément de congestion MTA", "ar": "رسوم ازدحام MTA",
  "pt": "Sobretaxa de congestionamento da MTA", "ur": "MTA congestion surcharge", "hi": "MTA भीड़ अधिभार", "bn": "MTA যানজট সারচার্জ",
  "ud": "MTA کنجیشن فیس", "zh": "MTA 拥堵附加费", "de": "MTA-Stauzuschlag", "it": "Supplemento di congestione MTA",
  "ru": "Надбавка MTA за пробки", "tr": "MTA trafik yoğunluğu ek ücreti", "ko": "MTA 혼잡 통행료", "ja": "MTA渋滞追加料金",
  "vi": "Phụ phí tắc nghẽn MTA", "fa": "هزینهٔ ازدحام MTA", "th": "ค่าธรรมเนียมจราจรหนาแน่น MTA"
};

NOEL_I18N["class.referral_discount"] = {
  "en": "Referral discount", "es": "Descuento por recomendación", "fr": "Remise de parrainage", "ar": "خصم الإحالة",
  "pt": "Desconto por indicação", "ur": "Referral discount", "hi": "रेफ़रल छूट", "bn": "রেফারেল ছাড়",
  "ud": "تجویزی رعایت", "zh": "推荐折扣", "de": "Empfehlungsrabatt", "it": "Sconto referral",
  "ru": "Реферальная скидка", "tr": "Referans indirimi", "ko": "추천 할인", "ja": "紹介割引",
  "vi": "Giảm giá giới thiệu", "fa": "تخفیف معرفی", "th": "ส่วนลดแนะนำ"
};

NOEL_I18N["class.discount_note"] = {
  "en": "Referral discount applied — 5% off your first ride.", "es": "Descuento por recomendación aplicado: 5 % de descuento en tu primer viaje.", "fr": "Remise de parrainage appliquée — 5 % de réduction sur votre premier trajet.", "ar": "تم تطبيق خصم الإحالة — خصم 5٪ على رحلتك الأولى.",
  "pt": "Desconto por indicação aplicado — 5% de desconto na sua primeira viagem.", "ur": "Referral discount lag gaya — pehli ride par 5% off.", "hi": "रेफ़रल छूट लागू — आपकी पहली सवारी पर 5% की छूट।", "bn": "রেফারেল ছাড় প্রযোজ্য — আপনার প্রথম রাইডে ৫% ছাড়।",
  "ud": "تجویزی رعایت لگا دی گئی ہے — آپ کی پہلی سواری پر 5% چھوٹ", "zh": "已应用推荐折扣——首次行程优惠5%。", "de": "Empfehlungsrabatt angewendet — 5 % Rabatt auf Ihre erste Fahrt.", "it": "Sconto referral applicato — 5% di sconto sulla tua prima corsa.",
  "ru": "Применена реферальная скидка — 5% скидка на вашу первую поездку.", "tr": "Referans indirimi uygulandı — ilk yolculuğunuzda %5 indirim.", "ko": "추천 할인이 적용되었습니다. 첫 이동 5% 할인.", "ja": "紹介割引が適用されました — 初回乗車が5%割引。",
  "vi": "Đã áp dụng giảm giá giới thiệu — giảm 5% cho chuyến đi đầu tiên của bạn.", "fa": "تخفیف معرفی اعمال شد — ۵٪ تخفیف برای اولین سفر شما", "th": "ใช้ส่วนลดแนะนำแล้ว — ลด 5% สำหรับการเดินทางครั้งแรกของคุณ"
};

NOEL_I18N["class.hl_comfort"] = {
  "en": "Clean, quiet, and executive-level comfort.", "es": "Comodidad limpia, silenciosa y de nivel ejecutivo.", "fr": "Un confort propre, silencieux et de niveau exécutif.", "ar": "راحة نظيفة وهادئة وبمستوى تنفيذي.",
  "pt": "Conforto limpo, silencioso e de nível executivo.", "ur": "Saaf, khamosh aur executive-level comfort.", "hi": "स्वच्छ, शांत और कार्यकारी स्तर का आराम।", "bn": "পরিষ্কার, শান্ত ও এক্সিকিউটিভ-স্তরের আরাম।",
  "ud": "صاف ستھری، پرسکون اور ایگزیکٹو سطح کا آرام", "zh": "干净、安静、高管级舒适。", "de": "Sauber, ruhig und Komfort auf Executive-Niveau.", "it": "Pulito, silenzioso e comfort di livello executive.",
  "ru": "Чисто, тихо и комфорт уровня executive.", "tr": "Temiz, sessiz ve yönetici düzeyinde konfor.", "ko": "깨끗하고 조용하며 임원급 편안함.", "ja": "清潔で静か、エグゼクティブレベルの快適さ。",
  "vi": "Sạch sẽ, yên tĩnh và thoải mái ở đẳng cấp điều hành.", "fa": "تمیز، آرام و راحتی در سطح اجرایی", "th": "สะอาด เงียบ และสะดวกสบายระดับผู้บริหาร"
};

NOEL_I18N["class.hl_charged"] = {
  "en": "Arrive fully charged", "es": "Llega con la batería llena", "fr": "Arrivez complètement chargé", "ar": "صِل وبطاريتك مشحونة بالكامل",
  "pt": "Chegue com a bateria cheia", "ur": "Full charge ke saath pahunchen", "hi": "पूरी तरह चार्ज होकर पहुँचें", "bn": "সম্পূর্ণ চার্জ নিয়ে পৌঁছান",
  "ud": "فون چارج شدہ حالت میں پہنچیں", "zh": "到达时手机充满电", "de": "Kommen Sie mit vollem Akku an", "it": "Arriva con il telefono carico",
  "ru": "Приезжайте с полностью заряженным телефоном", "tr": "Telefonunuz dolu olarak varın", "ko": "휴대폰 충전 완료 상태로 도착", "ja": "電話をフル充電で到着",
  "vi": "Đến nơi với điện thoại đầy pin", "fa": "با تلفن شارژشده برسید", "th": "ถึงที่หมายพร้อมโทรศัพท์เต็ม"
};

NOEL_I18N["class.hl_charged_text"] = {
  "en": "Phone chargers in every car, so your phone is full when you arrive.", "es": "Cargadores de teléfono en cada coche, para que tu teléfono esté lleno al llegar.", "fr": "Des chargeurs de téléphone dans chaque voiture, pour que votre téléphone soit chargé à votre arrivée.", "ar": "شواحن هواتف في كل سيارة، ليكون هاتفك مشحونًا بالكامل عند وصولك.",
  "pt": "Carregadores de celular em cada carro, para que seu telefone esteja carregado ao chegar.", "ur": "Har gaadi mein phone chargers, taaki aapka phone pahunchte waqt full ho.", "hi": "हर गाड़ी में फ़ोन चार्जर, ताकि पहुँचने पर आपका फ़ोन पूरा चार्ज हो।", "bn": "প্রতিটি গাড়িতে ফোন চার্জার, যাতে পৌঁছানোর সময় আপনার ফোন সম্পূর্ণ চার্জ থাকে।",
  "ud": "ہر گاڑی میں فون چارجر موجود ہے تاکہ آپ منزل پر پہنچیں تو فون چارج شدہ ہو", "zh": "每辆车都配有手机充电器，到达时您的手机将充满电。", "de": "Handyladegeräte in jedem Auto, damit Ihr Telefon bei der Ankunft voll aufgeladen ist.", "it": "Caricabatterie in ogni auto, così il telefono è carico all'arrivo.",
  "ru": "Зарядные устройства в каждом автомобиле, чтобы ваш телефон был полностью заряжен по прибытии.", "tr": "Her araçta telefon şarj cihazları var, böylece vardığınızda telefonunuz dolu olur.", "ko": "모든 차량에 휴대폰 충전기가 있어 도착 시 휴대폰이 완전히 충전되어 있습니다.", "ja": "すべての車に電話充電器があり、到着時には電話がフル充電されています。",
  "vi": "Bộ sạc điện thoại trên mọi xe, vì vậy điện thoại của bạn sẽ đầy pin khi đến nơi.", "fa": "در هر خودرو شارژر تلفن هست تا با تلفن شارژشده به مقصد برسید", "th": "ที่ชาร์จโทรศัพท์ในรถทุกคัน เพื่อให้โทรศัพท์ของคุณเต็มเมื่อถึงที่หมาย"
};

NOEL_I18N["class.cap_luggage_intro"] = {
  "en": "Based on standard luggage sizes, which may differ from yours.", "es": "Según los tamaños estándar de equipaje, que pueden diferir de los tuyos.", "fr": "Basé sur les tailles standard de bagages, qui peuvent différer des vôtres.", "ar": "بناءً على أحجام الأمتعة القياسية، التي قد تختلف عن أحجامك.",
  "pt": "Com base nos tamanhos padrão de bagagem, que podem diferir dos seus.", "ur": "Standard luggage sizes ke hisaab se, jo aapke se mukhtalif ho sakte hain.", "hi": "मानक सामान के आकार के आधार पर, जो आपके सामान से भिन्न हो सकता है।", "bn": "স্ট্যান্ডার্ড লাগেজের আকারের ভিত্তিতে, যা আপনার থেকে আলাদা হতে পারে।",
  "ud": "معیاری سامان کے سائز کی بنیاد پر، جو آپ کے سامان سے مختلف ہو سکتا ہے", "zh": "基于标准行李尺寸，可能与您的行李不同。", "de": "Basierend auf Standardgepäckgrößen, die von Ihren abweichen können.", "it": "In base alle dimensioni standard dei bagagli, che potrebbero differire dalle tue.",
  "ru": "Исходя из стандартных размеров багажа, которые могут отличаться от ваших.", "tr": "Standart bagaj boyutlarına göre; sizinkinden farklı olabilir.", "ko": "표준 수하물 크기를 기준으로 하며 고객님의 것과 다를 수 있습니다.", "ja": "標準的な荷物サイズに基づきます。お客様のものとは異なる場合があります。",
  "vi": "Dựa trên kích thước hành lý tiêu chuẩn, có thể khác với hành lý của bạn.", "fa": "بر اساس اندازهٔ استاندارد چمدان، که ممکن است با چمدان شما متفاوت باشد", "th": "อิงตามขนาดกระเป๋ามาตรฐาน ซึ่งอาจแตกต่างจากของคุณ"
};

NOEL_I18N["class.cap_seating_suffix"] = {
  "en": "— please respect the seating capacity for safety.", "es": "— respeta la capacidad de asientos por seguridad.", "fr": "— veuillez respecter la capacité d'accueil pour votre sécurité.", "ar": "— يرجى احترام سعة المقاعد من أجل السلامة.",
  "pt": "— respeite a capacidade de assentos por segurança.", "ur": "— safety ke liye seating capacity ka khayal rakhen.", "hi": "— सुरक्षा के लिए कृपया बैठने की क्षमता का सम्मान करें।", "bn": "— নিরাপত্তার জন্য আসনের ধারণক্ষমতা মেনে চলুন।",
  "ud": "— حفاظت کے لیے بیٹھنے کی گنجائش کا احترام کریں", "zh": "— 出于安全考虑，请遵守座位容量。", "de": "— bitte beachten Sie aus Sicherheitsgründen die Sitzplatzkapazität.", "it": "— per sicurezza, rispetta la capacità dei posti.",
  "ru": "— пожалуйста, соблюдайте вместимость мест из соображений безопасности.", "tr": "— güvenlik için lütfen oturma kapasitesine uyun.", "ko": "— 안전을 위해 좌석 정원을 준수해 주세요.", "ja": "— 安全のため、座席定員をお守りください。",
  "vi": "— vì lý do an toàn, vui lòng tôn trọng sức chứa ghế ngồi.", "fa": "— لطفاً برای ایمنی به ظرفیت صندلی احترام بگذارید", "th": "— โปรดเคารพความจุที่นั่งเพื่อความปลอดภัย"
};

NOEL_I18N["status.pay_unreachable"] = {
  "en": "Could not reach the payment service. Please try again.", "es": "No se pudo contactar con el servicio de pago. Inténtalo de nuevo.", "fr": "Impossible de joindre le service de paiement. Veuillez réessayer.", "ar": "تعذّر الوصول إلى خدمة الدفع. يرجى المحاولة مرة أخرى.",
  "pt": "Não foi possível acessar o serviço de pagamento. Tente novamente.", "ur": "Payment service se rabta nahi ho saka. Dobara try karen.", "hi": "भुगतान सेवा से संपर्क नहीं हो सका। कृपया फिर से प्रयास करें।", "bn": "পেমেন্ট পরিষেবার সঙ্গে যোগাযোগ করা যায়নি। আবার চেষ্টা করুন।",
  "ud": "ادائیگی سروس تک نہیں پہنچا جا سکا، براہ کرم دوبارہ کوشش کریں", "zh": "无法连接到支付服务。请重试。", "de": "Der Zahlungsdienst konnte nicht erreicht werden. Bitte versuchen Sie es erneut.", "it": "Non è stato possibile raggiungere il servizio di pagamento. Riprova.",
  "ru": "Не удалось связаться с платёжной службой. Пожалуйста, попробуйте снова.", "tr": "Ödeme hizmetine ulaşılamadı. Lütfen tekrar deneyin.", "ko": "결제 서비스에 연결할 수 없습니다. 다시 시도해 주세요.", "ja": "決済サービスに接続できませんでした。もう一度お試しください。",
  "vi": "Không thể kết nối đến dịch vụ thanh toán. Vui lòng thử lại.", "fa": "نمی‌توان به سرویس پرداخت رسید، لطفاً دوباره تلاش کنید", "th": "ไม่สามารถติดต่อบริการชำระเงินได้ โปรดลองอีกครั้ง"
};

NOEL_I18N["status.fill_card_fields"] = {
  "en": "Please fill in all card fields.", "es": "Completa todos los campos de la tarjeta.", "fr": "Veuillez remplir tous les champs de la carte.", "ar": "يرجى ملء جميع حقول البطاقة.",
  "pt": "Preencha todos os campos do cartão.", "ur": "Card ke saare fields bharen.", "hi": "कृपया कार्ड के सभी फ़ील्ड भरें।", "bn": "কার্ডের সব ঘর পূরণ করুন।",
  "ud": "براہ کرم کارڈ کے تمام فیلڈز بھریں", "zh": "请填写所有卡片字段。", "de": "Bitte füllen Sie alle Kartenfelder aus.", "it": "Compila tutti i campi della carta.",
  "ru": "Пожалуйста, заполните все поля карты.", "tr": "Lütfen tüm kart alanlarını doldurun.", "ko": "모든 카드 항목을 입력해 주세요.", "ja": "すべてのカード項目を入力してください。",
  "vi": "Vui lòng điền tất cả các trường của thẻ.", "fa": "لطفاً همهٔ فیلدهای کارت را پر کنید", "th": "โปรดกรอกข้อมูลบัตรให้ครบทุกช่อง"
};

NOEL_I18N["status.cancel_confirm"] = {
  "en": "Cancel this booking? The cancellation rules on this page apply.", "es": "¿Cancelar esta reserva? Se aplican las reglas de cancelación de esta página.", "fr": "Annuler cette réservation ? Les règles d'annulation de cette page s'appliquent.", "ar": "ألغِ هذا الحجز؟ تنطبق قواعد الإلغاء الموضحة في هذه الصفحة.",
  "pt": "Cancelar esta reserva? As regras de cancelamento desta página se aplicam.", "ur": "Ye booking cancel karen? Is page par likhe cancellation rules laagu honge.", "hi": "यह बुकिंग रद्द करें? इस पेज पर लिखे रद्दीकरण नियम लागू होंगे।", "bn": "এই বুকিং বাতিল করবেন? এই পাতায় লেখা বাতিলের নিয়ম প্রযোজ্য হবে।",
  "ud": "کیا آپ واقعی یہ بکنگ منسوخ کرنا چاہتے ہیں؟ اس صفحے پر منسوخی کے اصول لاگو ہوتے ہیں", "zh": "取消此预订？本页面的取消规则适用。", "de": "Diese Buchung stornieren? Es gelten die Stornierungsbedingungen auf dieser Seite.", "it": "Annullare questa prenotazione? Si applicano le regole di cancellazione di questa pagina.",
  "ru": "Отменить это бронирование? Применяются правила отмены на этой странице.", "tr": "Bu rezervasyonu iptal etmek istiyor musunuz? Bu sayfadaki iptal kuralları geçerlidir.", "ko": "이 예약을 취소하시겠습니까? 이 페이지의 취소 규정이 적용됩니다.", "ja": "この予約をキャンセルしますか？このページのキャンセル規定が適用されます。",
  "vi": "Hủy đặt xe này? Áp dụng quy định hủy xe trên trang này.", "fa": "آیا واقعاً می‌خواهید این رزرو را لغو کنید؟ قوانین لغو در این صفحه اعمال می‌شود", "th": "ยกเลิกการจองนี้หรือไม่? กฎการยกเลิกในหน้านี้มีผลบังคับใช้"
};

NOEL_I18N["status.payment_needed"] = {
  "en": "Payment needed to confirm your ride", "es": "Se necesita el pago para confirmar tu viaje", "fr": "Paiement requis pour confirmer votre trajet", "ar": "يلزم الدفع لتأكيد رحلتك",
  "pt": "Pagamento necessário para confirmar sua viagem", "ur": "Ride confirm karne ke liye payment zaroori hai", "hi": "आपकी सवारी की पुष्टि के लिए भुगतान आवश्यक है", "bn": "আপনার রাইড নিশ্চিত করতে পেমেন্ট প্রয়োজন",
  "ud": "اپنی سواری کی تصدیق کے لیے ادائیگی درکار ہے", "zh": "需要付款以确认您的行程", "de": "Zahlung erforderlich, um Ihre Fahrt zu bestätigen", "it": "Pagamento necessario per confermare la tua corsa",
  "ru": "Требуется оплата для подтверждения вашей поездки", "tr": "Yolculuğunuzu onaylamak için ödeme gerekli", "ko": "이동 확인을 위해 결제가 필요합니다", "ja": "乗車を確定するにはお支払いが必要です",
  "vi": "Cần thanh toán để xác nhận chuyến đi của bạn", "fa": "برای تأیید سفر خود، پرداخت لازم است", "th": "ต้องชำระเงินเพื่อยืนยันการเดินทางของคุณ"
};

NOEL_I18N["status.chauffeur_confirmed"] = {
  "en": "Chauffeur confirmed", "es": "Chófer confirmado", "fr": "Chauffeur confirmé", "ar": "تم تأكيد السائق",
  "pt": "Motorista confirmado", "ur": "Chauffeur confirm ho gaya", "hi": "शॉफ़र कन्फ़र्म हो गया", "bn": "শোফার নিশ্চিত হয়েছে",
  "ud": "ڈرائیور کی تصدیق ہو گئی", "zh": "司机已确认", "de": "Chauffeur bestätigt", "it": "Chauffeur confermato",
  "ru": "Шофёр подтверждён", "tr": "Şoför onaylandı", "ko": "쇼퍼 확인됨", "ja": "ショファーが確認されました",
  "vi": "Tài xế đã xác nhận", "fa": "راننده تأیید شد", "th": "ยืนยันคนขับแล้ว"
};

NOEL_I18N["status.arrived"] = {
  "en": "Your chauffeur has arrived", "es": "Tu chófer ha llegado", "fr": "Votre chauffeur est arrivé", "ar": "وصل سائقك",
  "pt": "Seu motorista chegou", "ur": "Aapka chauffeur aa gaya hai", "hi": "आपका शॉफ़र आ गया है", "bn": "আপনার শোফার পৌঁছেছেন",
  "ud": "آپ کا ڈرائیور پہنچ گیا ہے", "zh": "您的司机已到达", "de": "Ihr Chauffeur ist angekommen", "it": "Il tuo chauffeur è arrivato",
  "ru": "Ваш шофёр прибыл", "tr": "Şoförünüz geldi", "ko": "쇼퍼가 도착했습니다", "ja": "ショファーが到着しました",
  "vi": "Tài xế của bạn đã đến", "fa": "رانندهٔ شما رسیده است", "th": "คนขับของคุณมาถึงแล้ว"
};

NOEL_I18N["status.under_way"] = {
  "en": "Your ride is under way", "es": "Tu viaje está en curso", "fr": "Votre trajet est en cours", "ar": "رحلتك جارية الآن",
  "pt": "Sua viagem está em andamento", "ur": "Aapki ride chal rahi hai", "hi": "आपकी सवारी चल रही है", "bn": "আপনার রাইড চলছে",
  "ud": "آپ کی سواری جاری ہے", "zh": "您的行程正在进行中", "de": "Ihre Fahrt ist unterwegs", "it": "La tua corsa è in corso",
  "ru": "Ваша поездка в пути", "tr": "Yolculuğunuz devam ediyor", "ko": "이동이 진행 중입니다", "ja": "乗車中です",
  "vi": "Chuyến đi của bạn đang diễn ra", "fa": "سفر شما در جریان است", "th": "การเดินทางของคุณกำลังดำเนินอยู่"
};

NOEL_I18N["status.completed_thanks"] = {
  "en": "Ride completed — thank you", "es": "Viaje completado: gracias", "fr": "Trajet terminé — merci", "ar": "اكتملت الرحلة — شكرًا لك",
  "pt": "Viagem concluída — obrigado", "ur": "Ride complete ho gayi — shukriya", "hi": "सवारी पूरी हुई — धन्यवाद", "bn": "রাইড সম্পূর্ণ হয়েছে — ধন্যবাদ",
  "ud": "سواری مکمل ہو گئی — شکریہ", "zh": "行程已完成——谢谢", "de": "Fahrt abgeschlossen — vielen Dank", "it": "Corsa completata — grazie",
  "ru": "Поездка завершена — спасибо", "tr": "Yolculuk tamamlandı — teşekkürler", "ko": "이동 완료 — 감사합니다", "ja": "乗車が完了しました — ありがとうございます",
  "vi": "Chuyến đi đã hoàn thành — cảm ơn bạn", "fa": "سفر تکمیل شد — متشکریم", "th": "การเดินทางเสร็จสิ้น — ขอบคุณ"
};

NOEL_I18N["status.booking_cancelled"] = {
  "en": "This booking was cancelled", "es": "Esta reserva fue cancelada", "fr": "Cette réservation a été annulée", "ar": "تم إلغاء هذا الحجز",
  "pt": "Esta reserva foi cancelada", "ur": "Ye booking cancel ho gayi", "hi": "यह बुकिंग रद्द कर दी गई", "bn": "এই বুকিং বাতিল করা হয়েছে",
  "ud": "یہ بکنگ منسوخ کر دی گئی ہے", "zh": "此预订已取消", "de": "Diese Buchung wurde storniert", "it": "Questa prenotazione è stata annullata",
  "ru": "Это бронирование было отменено", "tr": "Bu rezervasyon iptal edildi", "ko": "이 예약이 취소되었습니다", "ja": "この予約はキャンセルされました",
  "vi": "Đặt xe này đã bị hủy", "fa": "این رزرو لغو شده است", "th": "การจองนี้ถูกยกเลิกแล้ว"
};

NOEL_I18N["status.no_show"] = {
  "en": "Marked as a no-show", "es": "Marcado como no presentado", "fr": "Marqué comme absent", "ar": "تم تسجيله كعدم حضور",
  "pt": "Marcado como não comparecimento", "ur": "No-show mark kiya gaya", "hi": "नो-शो के रूप में चिह्नित", "bn": "নো-শো হিসেবে চিহ্নিত",
  "ud": "نو شو کے طور پر نشان زد کریں", "zh": "已标记为未出现", "de": "Als Nichterscheinen markiert", "it": "Segnato come no-show",
  "ru": "Отмечено как неявка", "tr": "Gelmeme olarak işaretlendi", "ko": "노쇼로 표시됨", "ja": "ノーショーとして記録されました",
  "vi": "Đã đánh dấu là không đến", "fa": "علامت‌گذاری به‌عنوان عدم حضور", "th": "ทำเครื่องหมายว่าไม่มา"
};

NOEL_I18N["status.hours_suffix"] = {
  "en": "hour(s)", "es": "hora(s)", "fr": "heure(s)", "ar": "ساعة",
  "pt": "hora(s)", "ur": "hour(s)", "hi": "घंटे", "bn": "ঘণ্টা",
  "ud": "گھنٹے", "zh": "小时", "de": "Stunde(n)", "it": "ora(e)",
  "ru": "час(а)", "tr": "saat", "ko": "시간", "ja": "時間",
  "vi": "giờ", "fa": "ساعت", "th": "ชั่วโมง"
};

NOEL_I18N["status.pickup_label"] = {
  "en": "Pickup", "es": "Recogida", "fr": "Prise en charge", "ar": "الاستلام",
  "pt": "Embarque", "ur": "Pickup", "hi": "पिकअप", "bn": "পিকআপ",
  "ud": "پک اپ", "zh": "上车", "de": "Abholung", "it": "Ritiro",
  "ru": "Подача", "tr": "Biniş", "ko": "픽업", "ja": "乗車",
  "vi": "Đón", "fa": "سوارشدن", "th": "รับ"
};

NOEL_I18N["status.map_unavailable"] = {
  "en": "Live map is unavailable right now. Your chauffeur is on the way to {place}.", "es": "El mapa en vivo no está disponible ahora mismo. Tu chófer está en camino a {place}.", "fr": "La carte en direct n'est pas disponible pour le moment. Votre chauffeur est en route vers {place}.", "ar": "الخريطة المباشرة غير متاحة الآن. سائقك في الطريق إلى {place}.",
  "pt": "O mapa ao vivo não está disponível agora. Seu motorista está a caminho de {place}.", "ur": "Live map abhi available nahi hai. Aapka chauffeur {place} ki taraf aa raha hai.", "hi": "लाइव मैप अभी उपलब्ध नहीं है। आपका शॉफ़र {place} की ओर आ रहा है।", "bn": "লাইভ মানচিত্র এখন উপলব্ধ নয়। আপনার শোফার {place}-এর দিকে আসছেন।",
  "ud": "لائیو نقشہ ابھی دستیاب نہیں ہے۔ آپ کا ڈرائیور {place} کی طرف آ رہا ہے", "zh": "实时地图目前不可用。您的司机正在前往 {place} 的路上。", "de": "Die Live-Karte ist derzeit nicht verfügbar. Ihr Chauffeur ist auf dem Weg zu {place}.", "it": "La mappa live non è al momento disponibile. Il tuo chauffeur è in arrivo a {place}.",
  "ru": "Карта в реальном времени сейчас недоступна. Ваш шофёр едет к {place}.", "tr": "Canlı harita şu anda kullanılamıyor. Şoförünüz {place} adresine doğru yolda.", "ko": "실시간 지도를 현재 사용할 수 없습니다. 쇼퍼가 {place}(으)로 오고 있습니다.", "ja": "ライブマップは現在ご利用いただけません。ショファーが{place}へ向かっています。",
  "vi": "Bản đồ trực tiếp hiện không khả dụng. Tài xế của bạn đang trên đường đến {place}.", "fa": "نقشهٔ زنده در حال حاضر در دسترس نیست. رانندهٔ شما در راه {place} است", "th": "แผนที่สดไม่พร้อมใช้งานในขณะนี้ คนขับของคุณกำลังมุ่งหน้าไป {place}"
};

NOEL_I18N["status.map_pickup_point"] = {
  "en": "your pickup point", "es": "tu punto de recogida", "fr": "votre point de prise en charge", "ar": "نقطة الاستلام الخاصة بك",
  "pt": "seu ponto de embarque", "ur": "aapka pickup point", "hi": "आपका पिकअप पॉइंट", "bn": "আপনার পিকআপ পয়েন্ট",
  "ud": "آپ کا پک اپ پوائنٹ", "zh": "您的上车点", "de": "Ihrem Abholort", "it": "il tuo punto di partenza",
  "ru": "ваша точка подачи", "tr": "biniş noktanız", "ko": "픽업 지점", "ja": "お客様の乗車地点",
  "vi": "điểm đón của bạn", "fa": "نقطهٔ سوارشدن شما", "th": "จุดรับของคุณ"
};

NOEL_I18N["class.choose_experience"] = {
  "en": "Choose your experience", "es": "Elige tu experiencia", "fr": "Choisissez votre expérience", "ar": "اختر تجربتك",
  "pt": "Escolha sua experiência", "ur": "Apna experience chunen", "hi": "अपना अनुभव चुनें", "bn": "আপনার অভিজ্ঞতা বেছে নিন",
  "ud": "اپنا تجربہ منتخب کریں", "zh": "选择您的体验", "de": "Wählen Sie Ihr Erlebnis", "it": "Scegli la tua esperienza",
  "ru": "Выберите впечатление", "tr": "Deneyiminizi seçin", "ko": "경험 선택", "ja": "エクスペリエンスを選択",
  "vi": "Chọn trải nghiệm của bạn", "fa": "تجربهٔ خود را انتخاب کنید", "th": "เลือกประสบการณ์ของคุณ"
};

NOEL_I18N["class.choose_vehicle"] = {
  "en": "Choose your vehicle class", "es": "Elige la clase de tu vehículo", "fr": "Choisissez la classe de votre véhicule", "ar": "اختر فئة مركبتك",
  "pt": "Escolha a classe do seu veículo", "ur": "Apni gaadi ki class chunen", "hi": "अपने वाहन की श्रेणी चुनें", "bn": "আপনার গাড়ির শ্রেণি বেছে নিন",
  "ud": "اپنی گاڑی کی کلاس منتخب کریں", "zh": "选择您的车辆级别", "de": "Wählen Sie Ihre Fahrzeugklasse", "it": "Scegli la classe del veicolo",
  "ru": "Выберите класс автомобиля", "tr": "Araç sınıfınızı seçin", "ko": "차량 클래스 선택", "ja": "車両クラスを選択",
  "vi": "Chọn hạng xe của bạn", "fa": "کلاس خودروی خود را انتخاب کنید", "th": "เลือกระดับรถยนต์ของคุณ"
};

NOEL_I18N["class.explore"] = {
  "en": "Explore {label} details", "es": "Ver detalles de {label}", "fr": "Découvrir les détails de {label}", "ar": "استكشف تفاصيل {label}",
  "pt": "Ver detalhes de {label}", "ur": "{label} ki details dekhen", "hi": "{label} का विवरण देखें", "bn": "{label}-এর বিবরণ দেখুন",
  "ud": "{label} کی تفصیل دیکھیں", "zh": "查看{label}详情", "de": "{label}-Details ansehen", "it": "Vedi i dettagli di {label}",
  "ru": "Подробнее о {label}", "tr": "{label} ayrıntılarını keşfedin", "ko": "{label} 자세히 보기", "ja": "{label}の詳細を見る",
  "vi": "Khám phá chi tiết {label}", "fa": "مشاهدهٔ جزئیات {label}", "th": "สำรวจรายละเอียด {label}"
};

NOEL_I18N["class.whats_included"] = {
  "en": "What's included", "es": "Qué incluye", "fr": "Ce qui est inclus", "ar": "ما المشمول",
  "pt": "O que está incluído", "ur": "Is mein kya hai", "hi": "इसमें क्या शामिल है", "bn": "কী কী অন্তর্ভুক্ত",
  "ud": "کیا شامل ہے", "zh": "包含内容", "de": "Was ist enthalten", "it": "Cosa è incluso",
  "ru": "Что включено", "tr": "Neler dahil", "ko": "포함 사항", "ja": "含まれるもの",
  "vi": "Bao gồm những gì", "fa": "چه چیزی شامل است", "th": "สิ่งที่รวมอยู่"
};

NOEL_I18N["class.included_1"] = {
  "en": "Personal meet & greet", "es": "Recibimiento personal", "fr": "Accueil personnalisé", "ar": "استقبال شخصي",
  "pt": "Recepção pessoal", "ur": "Personal meet & greet", "hi": "व्यक्तिगत स्वागत", "bn": "ব্যক্তিগত অভ্যর্থনা",
  "ud": "ذاتی استقبال", "zh": "专人迎接", "de": "Persönlicher Empfang", "it": "Accoglienza personale",
  "ru": "Личная встреча", "tr": "Kişisel karşılama", "ko": "직접 맞이 서비스", "ja": "パーソナルな出迎え",
  "vi": "Đón tiếp trực tiếp", "fa": "استقبال شخصی", "th": "ต้อนรับส่วนตัว"
};

NOEL_I18N["class.included_2"] = {
  "en": "Includes up to 15 minutes of free wait time", "es": "Incluye hasta 15 minutos de espera gratis", "fr": "Jusqu'à 15 minutes d'attente gratuite incluses", "ar": "يشمل حتى 15 دقيقة انتظار مجاني",
  "pt": "Inclui até 15 minutos de espera gratuita", "ur": "15 minutes tak free wait time shamil hai", "hi": "15 मिनट तक मुफ़्त प्रतीक्षा समय शामिल है", "bn": "১৫ মিনিট পর্যন্ত বিনামূল্যে অপেক্ষার সময় অন্তর্ভুক্ত",
  "ud": "15 منٹ تک مفت انتظار شامل ہے", "zh": "包含最多15分钟免费等候时间", "de": "Bis zu 15 Minuten kostenlose Wartezeit inklusive", "it": "Fino a 15 minuti di attesa gratuita inclusi",
  "ru": "До 15 минут бесплатного ожидания включено", "tr": "15 dakikaya kadar ücretsiz bekleme dahildir", "ko": "최대 15분 무료 대기 포함", "ja": "最大15分の無料待ち時間を含む",
  "vi": "Bao gồm tối đa 15 phút chờ miễn phí", "fa": "تا ۱۵ دقیقه انتظار رایگان شامل است", "th": "รวมเวลารอฟรีสูงสุด 15 นาที"
};

NOEL_I18N["class.included_3"] = {
  "en": "Free to cancel up to 1 hour before pickup", "es": "Cancelación gratis hasta 1 hora antes de la recogida", "fr": "Annulation gratuite jusqu'à 1 heure avant la prise en charge", "ar": "إلغاء مجاني حتى ساعة واحدة قبل الاستلام",
  "pt": "Cancelamento gratuito até 1 hora antes do embarque", "ur": "Pickup se 1 hour pehle tak free cancel", "hi": "पिकअप से 1 घंटे पहले तक मुफ़्त रद्द करें", "bn": "পিকআপের ১ ঘণ্টা আগে পর্যন্ত বিনামূল্যে বাতিল",
  "ud": "پک اپ سے 1 گھنٹہ پہلے تک مفت منسوخی", "zh": "上车前1小时内免费取消", "de": "Kostenlose Stornierung bis 1 Stunde vor der Abholung", "it": "Cancellazione gratuita fino a 1 ora prima del ritiro",
  "ru": "Бесплатная отмена до 1 часа до подачи", "tr": "Binişten 1 saate kadar ücretsiz iptal", "ko": "픽업 1시간 전까지 무료 취소", "ja": "乗車の1時間前まで無料キャンセル",
  "vi": "Hủy miễn phí đến 1 giờ trước giờ đón", "fa": "لغو رایگان تا ۱ ساعت پیش از سوارشدن", "th": "ยกเลิกฟรีถึง 1 ชั่วโมงก่อนเวลารับ"
};

NOEL_I18N["class.included_4"] = {
  "en": "iOS and Android chargers onboard", "es": "Cargadores para iOS y Android a bordo", "fr": "Chargeurs iOS et Android à bord", "ar": "شواحن iOS وأندرويد على متن السيارة",
  "pt": "Carregadores para iOS e Android a bordo", "ur": "iOS aur Android chargers onboard", "hi": "iOS और Android चार्जर ऑनबोर्ड", "bn": "iOS ও Android চার্জার অনবোর্ড",
  "ud": "گاڑی میں iOS اور Android چارجر", "zh": "车上配有 iOS 和 Android 充电器", "de": "iOS- und Android-Ladegeräte an Bord", "it": "Caricabatterie iOS e Android a bordo",
  "ru": "Зарядные устройства iOS и Android на борту", "tr": "Araçta iOS ve Android şarj cihazları", "ko": "차량 내 iOS 및 Android 충전기", "ja": "車内にiOSおよびAndroid充電器",
  "vi": "Bộ sạc iOS và Android trên xe", "fa": "شارژر iOS و Android در خودرو", "th": "ที่ชาร์จ iOS และ Android ในรถ"
};

NOEL_I18N["class.included_5"] = {
  "en": "Assistance with luggage at pickup and drop-off", "es": "Ayuda con el equipaje en la recogida y la llegada", "fr": "Aide avec les bagages à la prise en charge et à l'arrivée", "ar": "مساعدة في الأمتعة عند الاستلام والوصول",
  "pt": "Ajuda com a bagagem no embarque e no desembarque", "ur": "Pickup aur drop-off par luggage mein madad", "hi": "पिकअप और ड्रॉप-ऑफ़ पर सामान में सहायता", "bn": "পিকআপ ও ড্রপ-অফে লাগেজে সাহায্য",
  "ud": "پک اپ اور ڈراپ آف پر سامان میں مدد", "zh": "上车和下车时协助搬运行李", "de": "Hilfe mit dem Gepäck bei Abholung und Ankunft", "it": "Assistenza con i bagagli al ritiro e alla consegna",
  "ru": "Помощь с багажом при подаче и высадке", "tr": "Biniş ve inişte bagaj yardımı", "ko": "픽업 및 하차 시 수하물 도움", "ja": "乗車時と降車時の荷物のお手伝い",
  "vi": "Hỗ trợ hành lý khi đón và trả khách", "fa": "کمک با چمدان در سوارشدن و پیاده‌شدن", "th": "ช่วยเหลือกระเป๋าเมื่อรับและส่ง"
};

NOEL_I18N["class.capacity"] = {
  "en": "Capacity", "es": "Capacidad", "fr": "Capacité", "ar": "السعة",
  "pt": "Capacidade", "ur": "Capacity", "hi": "क्षमता", "bn": "ধারণক্ষমতা",
  "ud": "گنجائش", "zh": "容量", "de": "Kapazität", "it": "Capacità",
  "ru": "Вместимость", "tr": "Kapasite", "ko": "정원", "ja": "定員",
  "vi": "Sức chứa", "fa": "ظرفیت", "th": "ความจุ"
};

NOEL_I18N["class.luggage"] = {
  "en": "Luggage", "es": "Equipaje", "fr": "Bagages", "ar": "الأمتعة",
  "pt": "Bagagem", "ur": "Luggage", "hi": "सामान", "bn": "লাগেজ",
  "ud": "سامان", "zh": "行李", "de": "Gepäck", "it": "Bagagli",
  "ru": "Багаж", "tr": "Bagaj", "ko": "수하물", "ja": "荷物",
  "vi": "Hành lý", "fa": "چمدان", "th": "กระเป๋า"
};

NOEL_I18N["class.seating"] = {
  "en": "Seating", "es": "Asientos", "fr": "Places", "ar": "المقاعد",
  "pt": "Assentos", "ur": "Seating", "hi": "सीटें", "bn": "আসন",
  "ud": "نشستیں", "zh": "座位", "de": "Sitzplätze", "it": "Posti",
  "ru": "Места", "tr": "Oturma", "ko": "좌석", "ja": "座席",
  "vi": "Chỗ ngồi", "fa": "صندلی", "th": "ที่นั่ง"
};

NOEL_I18N["class.passengers"] = {
  "en": "{n} passengers", "es": "{n} pasajeros", "fr": "{n} passagers", "ar": "{n} ركاب",
  "pt": "{n} passageiros", "ur": "{n} passengers", "hi": "{n} यात्री", "bn": "{n} জন যাত্রী",
  "ud": "{n} مسافر", "zh": "{n} 位乘客", "de": "{n} Passagiere", "it": "{n} passeggeri",
  "ru": "{n} пассажиров", "tr": "{n} yolcu", "ko": "{n}명 승객", "ja": "{n}名の乗客",
  "vi": "{n} hành khách", "fa": "{n} مسافر", "th": "{n} ผู้โดยสาร"
};

NOEL_I18N["class.breakdown"] = {
  "en": "Price breakdown", "es": "Desglose del precio", "fr": "Détail du prix", "ar": "تفصيل السعر",
  "pt": "Detalhamento do preço", "ur": "Price breakdown", "hi": "मूल्य विवरण", "bn": "মূল্যের বিবরণ",
  "ud": "قیمت کی تفصیل", "zh": "价格明细", "de": "Preisaufschlüsselung", "it": "Dettaglio del prezzo",
  "ru": "Разбивка цены", "tr": "Fiyat dökümü", "ko": "요금 내역", "ja": "料金内訳",
  "vi": "Chi tiết giá", "fa": "جزئیات قیمت", "th": "รายละเอียดราคา"
};

NOEL_I18N["class.base_fare"] = {
  "en": "Base fare", "es": "Tarifa base", "fr": "Tarif de base", "ar": "الأجرة الأساسية",
  "pt": "Tarifa base", "ur": "Base fare", "hi": "आधार किराया", "bn": "মূল ভাড়া",
  "ud": "بنیادی کرایہ", "zh": "基本费用", "de": "Grundpreis", "it": "Tariffa base",
  "ru": "Базовый тариф", "tr": "Temel ücret", "ko": "기본 요금", "ja": "基本料金",
  "vi": "Giá cơ bản", "fa": "کرایهٔ پایه", "th": "ค่าโดยสารพื้นฐาน"
};

NOEL_I18N["class.airport_fee"] = {
  "en": "Airport access fee", "es": "Tasa de acceso al aeropuerto", "fr": "Frais d'accès à l'aéroport", "ar": "رسوم دخول المطار",
  "pt": "Taxa de acesso ao aeroporto", "ur": "Airport access fee", "hi": "एयरपोर्ट प्रवेश शुल्क", "bn": "বিমানবন্দর প্রবেশ ফি",
  "ud": "ہوائی اڈے کی رسائی فیس", "zh": "机场使用费", "de": "Flughafenzugangsgebühr", "it": "Supplemento di accesso all'aeroporto",
  "ru": "Сбор за доступ в аэропорт", "tr": "Havalimanı erişim ücreti", "ko": "공항 이용료", "ja": "空港利用料",
  "vi": "Phí vào sân bay", "fa": "هزینهٔ دسترسی به فرودگاه", "th": "ค่าธรรมเนียมเข้าสนามบิน"
};

NOEL_I18N["class.black_car_fee"] = {
  "en": "Black car fee", "es": "Tasa de coche negro", "fr": "Frais de voiture noire", "ar": "رسوم السيارة السوداء",
  "pt": "Taxa de carro preto", "ur": "Black car fee", "hi": "ब्लैक कार शुल्क", "bn": "ব্ল্যাক কার ফি",
  "ud": "بلیک کار فیس", "zh": "专车费", "de": "Black-Car-Gebühr", "it": "Supplemento black car",
  "ru": "Сбор за чёрный автомобиль", "tr": "Black car ücreti", "ko": "블랙카 수수료", "ja": "ブラックカー料金",
  "vi": "Phí xe black car", "fa": "هزینهٔ خودروی بلک‌کار", "th": "ค่าธรรมเนียมรถ black car"
};

NOEL_I18N["class.sales_tax"] = {
  "en": "Sales tax", "es": "Impuesto sobre las ventas", "fr": "Taxe de vente", "ar": "ضريبة المبيعات",
  "pt": "Imposto sobre vendas", "ur": "Sales tax", "hi": "बिक्री कर", "bn": "বিক্রয় কর",
  "ud": "سیلز ٹیکس", "zh": "销售税", "de": "Verkaufssteuer", "it": "Imposta sulle vendite",
  "ru": "Налог с продаж", "tr": "Satış vergisi", "ko": "판매세", "ja": "売上税",
  "vi": "Thuế bán hàng", "fa": "مالیات فروش", "th": "ภาษีขาย"
};

NOEL_I18N["class.congestion"] = {
  "en": "Congestion", "es": "Congestión", "fr": "Congestion", "ar": "ازدحام",
  "pt": "Congestionamento", "ur": "Congestion", "hi": "भीड़ शुल्क", "bn": "যানজট",
  "ud": "کنجیشن فیس", "zh": "拥堵费", "de": "Stauzuschlag", "it": "Congestione",
  "ru": "Пробки", "tr": "Trafik yoğunluğu", "ko": "혼잡 통행료", "ja": "渋滞追加料金",
  "vi": "Phí tắc nghẽn", "fa": "هزینهٔ ازدحام", "th": "ค่าธรรมเนียมจราจรหนาแน่น"
};

NOEL_I18N["class.toll"] = {
  "en": "Toll", "es": "Peaje", "fr": "Péage", "ar": "رسوم الطرق",
  "pt": "Pedágio", "ur": "Toll", "hi": "टोल", "bn": "টোল",
  "ud": "ٹول", "zh": "过路费", "de": "Maut", "it": "Pedaggio",
  "ru": "Платная дорога", "tr": "Geçiş ücreti", "ko": "통행료", "ja": "通行料",
  "vi": "Phí cầu đường", "fa": "عوارض", "th": "ค่าผ่านทาง"
};

NOEL_I18N["class.total"] = {
  "en": "Total", "es": "Total", "fr": "Total", "ar": "المجموع",
  "pt": "Total", "ur": "Total", "hi": "कुल", "bn": "মোট",
  "ud": "کل", "zh": "总计", "de": "Gesamt", "it": "Totale",
  "ru": "Итого", "tr": "Toplam", "ko": "합계", "ja": "合計",
  "vi": "Tổng cộng", "fa": "مجموع", "th": "ยอดรวม"
};

NOEL_I18N["class.please_note"] = {
  "en": "Please note", "es": "Ten en cuenta", "fr": "Veuillez noter", "ar": "يرجى الملاحظة",
  "pt": "Observação", "ur": "Please note", "hi": "कृपया ध्यान दें", "bn": "অনুগ্রহ করে লক্ষ্য করুন",
  "ud": "براہ کرم نوٹ کریں", "zh": "请注意", "de": "Bitte beachten", "it": "Nota bene",
  "ru": "Обратите внимание", "tr": "Lütfen dikkat", "ko": "참고 사항", "ja": "ご注意ください",
  "vi": "Xin lưu ý", "fa": "لطفاً توجه کنید", "th": "โปรดทราบ"
};

NOEL_I18N["class.note_1"] = {
  "en": "Your estimated total fare is based on the trip details shown above. The final fare may change if you change the pickup or drop-off location, change the vehicle type, or a different route is taken.", "es": "La tarifa total estimada se basa en los detalles del viaje mostrados arriba. La tarifa final puede cambiar si cambias el lugar de recogida o destino, el tipo de vehículo o si se toma otra ruta.", "fr": "Le tarif total estimé est basé sur les détails du trajet ci-dessus. Le tarif final peut changer si vous modifiez le lieu de prise en charge ou de destination, le type de véhicule, ou si un autre itinéraire est emprunté.", "ar": "الأجرة الإجمالية التقديرية مبنية على تفاصيل الرحلة أعلاه. قد تتغير الأجرة النهائية إذا غيّرت مكان الاستلام أو الوصول أو نوع المركبة أو سُلك طريق مختلف.",
  "pt": "A tarifa total estimada baseia-se nos detalhes da viagem acima. A tarifa final pode mudar se você alterar o local de embarque ou destino, o tipo de veículo ou se outra rota for seguida.", "ur": "Aapka estimated total fare upar dikhaye gaye trip details par hai. Final fare badal sakta hai agar aap pickup ya drop-off jagah, gaadi ki type badal dein ya koi doosra route liya jaye.", "hi": "आपका अनुमानित कुल किराया ऊपर दिखाए गए यात्रा विवरण पर आधारित है। अंतिम किराया बदल सकता है यदि आप पिकअप या ड्रॉप-ऑफ़ स्थान, वाहन का प्रकार बदलते हैं या कोई दूसरा रास्ता लिया जाता है।", "bn": "আপনার আনুমানিক মোট ভাড়া উপরে দেখানো ট্রিপের বিবরণের ভিত্তিতে। পিকআপ বা ড্রপ-অফের জায়গা, গাড়ির ধরন বদলালে বা অন্য রুট নিলে চূড়ান্ত ভাড়া বদলে যেতে পারে।",
  "ud": "آپ کا تخمینی کل کرایہ اوپر دکھائی گئی سواری کی تفصیل پر مبنی ہے۔ اگر آپ پک اپ یا ڈراپ آف کی جگہ تبدیل کریں، گاڑی کی قسم بدلیں، یا مختلف راستہ استعمال کریں تو حتمی کرایہ تبدیل ہو سکتا ہے", "zh": "您的预估总费用基于上方显示的行程详情。如果您更改上车或下车地点、更改车辆类型或采取不同路线，最终费用可能会发生变化。", "de": "Ihr geschätzter Gesamtpreis basiert auf den oben angegebenen Reisedetails. Der endgültige Preis kann sich ändern, wenn Sie den Abhol- oder Zielort ändern, den Fahrzeugtyp wechseln oder eine andere Route genommen wird.", "it": "La tariffa totale stimata si basa sui dettagli del viaggio mostrati sopra. La tariffa finale può cambiare se modifichi il luogo di partenza o di destinazione, il tipo di veicolo o se viene preso un percorso diverso.",
  "ru": "Ваша предполагаемая общая стоимость рассчитана на основе данных поездки, указанных выше. Итоговая стоимость может измениться, если вы измените адрес отправления или назначения, тип автомобиля или будет выбран другой маршрут.", "tr": "Tahmini toplam ücretiniz yukarıda gösterilen yolculuk ayrıntılarına dayanmaktadır. Biniş veya varış yerini değiştirirseniz, araç türünü değiştirirseniz veya farklı bir rota izlenirse nihai ücret değişebilir.", "ko": "예상 총 요금은 위에 표시된 이동 정보를 기준으로 합니다. 출발지나 목적지를 변경하거나 차량 종류를 바꾸거나 다른 경로를 이용하면 최종 요금이 달라질 수 있습니다.", "ja": "推定合計料金は、上記に表示された乗車詳細に基づきます。出発地または目的地を変更したり、車両タイプを変更したり、別のルートを取ったりすると、最終料金が変わる場合があります。",
  "vi": "Tổng giá ước tính của bạn dựa trên chi tiết chuyến đi hiển thị ở trên. Giá cuối cùng có thể thay đổi nếu bạn thay đổi địa điểm đón hoặc trả khách, thay đổi loại xe hoặc đi theo tuyến đường khác.", "fa": "مجموع تقریبی کرایهٔ شما بر اساس جزئیات سفر نشان‌داده‌شده در بالاست. اگر مکان سوارشدن یا پیاده‌شدن را تغییر دهید، نوع خودرو را عوض کنید یا از مسیر دیگری استفاده کنید، کرایهٔ نهایی ممکن است تغییر کند", "th": "ค่าโดยสารรวมโดยประมาณของคุณอิงตามรายละเอียดการเดินทางที่แสดงด้านบน ค่าโดยสารสุดท้ายอาจเปลี่ยนแปลงหากคุณเปลี่ยนสถานที่ต้นทางหรือปลายทาง เปลี่ยนประเภทรถยนต์ หรือใช้เส้นทางอื่น"
};

NOEL_I18N["class.note_2"] = {
  "en": "Guest and luggage capacities must be respected for safety reasons. If you are unsure, select a larger class.", "es": "Por seguridad, se deben respetar las capacidades de pasajeros y equipaje. Si no estás seguro, elige una clase mayor.", "fr": "Pour des raisons de sécurité, les capacités en passagers et en bagages doivent être respectées. En cas de doute, choisissez une classe supérieure.", "ar": "يجب احترام سعة الركاب والأمتعة لأسباب تتعلق بالسلامة. إذا لم تكن متأكدًا، فاختر فئة أكبر.",
  "pt": "Por segurança, as capacidades de passageiros e bagagem devem ser respeitadas. Se não tiver certeza, escolha uma classe maior.", "ur": "Safety ke liye guest aur luggage ki capacity ka khayal rakhen. Agar sure nahi hain to badi class chunen.", "hi": "सुरक्षा के लिए यात्रियों और सामान की क्षमता का सम्मान करें। यदि अनिश्चित हैं, तो बड़ी श्रेणी चुनें।", "bn": "নিরাপত্তার জন্য যাত্রী ও লাগেজের ধারণক্ষমতা মেনে চলুন। নিশ্চিত না হলে বড় শ্রেণি বেছে নিন।",
  "ud": "حفاظت کے لیے مسافروں اور سامان کی گنجائش کا احترام کرنا ضروری ہے۔ اگر یقین نہ ہو تو بڑی کلاس منتخب کریں", "zh": "出于安全原因，必须遵守乘客和行李容量。如果不确定，请选择更大的级别。", "de": "Die Kapazitäten für Gäste und Gepäck müssen aus Sicherheitsgründen eingehalten werden. Wenn Sie unsicher sind, wählen Sie eine größere Klasse.", "it": "Le capacità di ospiti e bagagli devono essere rispettate per motivi di sicurezza. Se non sei sicuro, seleziona una classe superiore.",
  "ru": "Вместимость для гостей и багажа должна соблюдаться из соображений безопасности. Если вы не уверены, выберите класс побольше.", "tr": "Güvenlik nedeniyle yolcu ve bagaj kapasitelerine uyulmalıdır. Emin değilseniz daha büyük bir sınıf seçin.", "ko": "안전을 위해 승객 및 수하물 정원을 준수해야 합니다. 확실하지 않으면 더 큰 클래스를 선택하세요.", "ja": "安全のため、乗客と荷物の定員を守る必要があります。ご不明な場合は、より大きなクラスを選択してください。",
  "vi": "Sức chứa khách và hành lý phải được tôn trọng vì lý do an toàn. Nếu bạn không chắc, hãy chọn hạng lớn hơn.", "fa": "برای ایمنی باید به ظرفیت مسافر و چمدان احترام گذاشت. اگر مطمئن نیستید، کلاس بزرگ‌تر را انتخاب کنید", "th": "ต้องเคารพความจุผู้โดยสารและกระเป๋าเพื่อความปลอดภัย หากไม่แน่ใจ โปรดเลือกระดับที่ใหญ่กว่า"
};

NOEL_I18N["class.note_3"] = {
  "en": "The vehicle images above are examples. You may get a different vehicle of similar quality.", "es": "Las imágenes de los vehículos son ejemplos. Es posible que recibas un vehículo diferente de calidad similar.", "fr": "Les images des véhicules ci-dessus sont des exemples. Vous pouvez recevoir un véhicule différent de qualité similaire.", "ar": "صور المركبات أعلاه أمثلة فقط. قد تحصل على مركبة مختلفة بجودة مماثلة.",
  "pt": "As imagens dos veículos acima são exemplos. Você pode receber um veículo diferente de qualidade similar.", "ur": "Upar dikhayi gayi gaadiyon ki photos examples hain. Aapko same quality ki koi doosri gaadi mil sakti hai.", "hi": "ऊपर दिखाए गए वाहनों की तस्वीरें उदाहरण हैं। आपको समान गुणवत्ता वाला कोई दूसरा वाहन मिल सकता है।", "bn": "উপরের গাড়ির ছবিগুলো উদাহরণ মাত্র। আপনি একই মানের অন্য গাড়ি পেতে পারেন।",
  "ud": "اوپر کی گاڑی کی تصویر صرف ایک مثال ہے۔ آپ کو اسی طرح کی معیار کی کوئی اور گاڑی مل سکتی ہے", "zh": "上方车辆图片仅为示例。您可能会得到一辆质量相似的不同车辆。", "de": "Die Fahrzeugbilder oben sind Beispiele. Sie erhalten möglicherweise ein anderes Fahrzeug von ähnlicher Qualität.", "it": "Le immagini dei veicoli sopra sono esempi. Potresti ricevere un veicolo diverso di qualità simile.",
  "ru": "Изображения автомобилей выше — примеры. Вам может быть предоставлен другой автомобиль аналогичного качества.", "tr": "Yukarıdaki araç görselleri örnektir. Benzer kalitede farklı bir araç alabilirsiniz.", "ko": "위의 차량 이미지는 예시입니다. 비슷한 품질의 다른 차량이 배정될 수 있습니다.", "ja": "上記の車両画像は例です。類似の品質の別の車両になる場合があります。",
  "vi": "Hình ảnh xe ở trên chỉ là ví dụ. Bạn có thể nhận được một xe khác có chất lượng tương tự.", "fa": "عکس خودرو در بالا فقط یک نمونه است. ممکن است خودروی دیگری با کیفیتی مشابه دریافت کنید", "th": "ภาพรถยนต์ด้านบนเป็นตัวอย่าง คุณอาจได้รับรถยนต์คันอื่นที่มีคุณภาพใกล้เคียงกัน"
};

NOEL_I18N["class.select"] = {
  "en": "Select {label}", "es": "Seleccionar {label}", "fr": "Choisir {label}", "ar": "اختر {label}",
  "pt": "Selecionar {label}", "ur": "{label} select karen", "hi": "{label} चुनें", "bn": "{label} বেছে নিন",
  "ud": "{label} منتخب کریں", "zh": "选择{label}", "de": "{label} auswählen", "it": "Seleziona {label}",
  "ru": "Выбрать {label}", "tr": "{label} seçin", "ko": "{label} 선택", "ja": "{label}を選択",
  "vi": "Chọn {label}", "fa": "{label} را انتخاب کنید", "th": "เลือก {label}"
};

NOEL_I18N["class.your_details"] = {
  "en": "Your details", "es": "Tus datos", "fr": "Vos coordonnées", "ar": "بياناتك",
  "pt": "Seus dados", "ur": "Aapki details", "hi": "आपका विवरण", "bn": "আপনার বিবরণ",
  "ud": "آپ کی تفصیلات", "zh": "您的信息", "de": "Ihre Daten", "it": "I tuoi dati",
  "ru": "Ваши данные", "tr": "Bilgileriniz", "ko": "고객님의 정보", "ja": "お客様の詳細",
  "vi": "Thông tin của bạn", "fa": "جزئیات شما", "th": "รายละเอียดของคุณ"
};

NOEL_I18N["class.your_name"] = {
  "en": "Your name", "es": "Tu nombre", "fr": "Votre nom", "ar": "اسمك",
  "pt": "Seu nome", "ur": "Aapka naam", "hi": "आपका नाम", "bn": "আপনার নাম",
  "ud": "آپ کا نام", "zh": "您的姓名", "de": "Ihr Name", "it": "Il tuo nome",
  "ru": "Ваше имя", "tr": "Adınız", "ko": "이름", "ja": "お名前",
  "vi": "Tên của bạn", "fa": "نام شما", "th": "ชื่อของคุณ"
};

NOEL_I18N["class.phone"] = {
  "en": "Phone number", "es": "Número de teléfono", "fr": "Numéro de téléphone", "ar": "رقم الهاتف",
  "pt": "Número de telefone", "ur": "Phone number", "hi": "फ़ोन नंबर", "bn": "ফোন নম্বর",
  "ud": "فون نمبر", "zh": "电话号码", "de": "Telefonnummer", "it": "Numero di telefono",
  "ru": "Номер телефона", "tr": "Telefon numarası", "ko": "전화번호", "ja": "電話番号",
  "vi": "Số điện thoại", "fa": "شماره تلفن", "th": "หมายเลขโทรศัพท์"
};

NOEL_I18N["class.email"] = {
  "en": "Email", "es": "Correo electrónico", "fr": "E-mail", "ar": "البريد الإلكتروني",
  "pt": "E-mail", "ur": "Email", "hi": "ईमेल", "bn": "ইমেইল",
  "ud": "ای میل", "zh": "电子邮件", "de": "E-Mail", "it": "Email",
  "ru": "Электронная почта", "tr": "E-posta", "ko": "이메일", "ja": "メール",
  "vi": "Email", "fa": "ایمیل", "th": "อีเมล"
};

NOEL_I18N["class.signin_expired"] = {
  "en": "Your sign-in expired — please tap Continue again.", "es": "Tu sesión caducó. Toca Continuar de nuevo.", "fr": "Votre connexion a expiré — veuillez appuyer à nouveau sur Continuer.", "ar": "انتهت صلاحية تسجيل دخولك — يرجى الضغط على متابعة مرة أخرى.",
  "pt": "Sua sessão expirou — toque em Continuar novamente.", "ur": "Aapka sign-in expire ho gaya — dobara Continue dabayen.", "hi": "आपका साइन-इन समाप्त हो गया — कृपया फिर से जारी रखें दबाएँ।", "bn": "আপনার সাইন-ইন মেয়াদ শেষ হয়েছে — আবার চালিয়ে যান চাপুন।",
  "ud": "آپ کا سائن ان ختم ہو گیا ہے — براہ کرم دوبارہ جاری رکھیں پر ٹیپ کریں", "zh": "您的登录已过期——请再次点击“继续”。", "de": "Ihre Anmeldung ist abgelaufen — bitte tippen Sie erneut auf Weiter.", "it": "Il tuo accesso è scaduto — tocca di nuovo Continua.",
  "ru": "Ваш вход истёк — пожалуйста, нажмите «Продолжить» ещё раз.", "tr": "Girişinizin süresi doldu — lütfen Devam'a tekrar dokunun.", "ko": "로그인이 만료되었습니다. 계속을 다시 눌러주세요.", "ja": "サインインの有効期限が切れました。「続ける」をもう一度タップしてください。",
  "vi": "Phiên đăng nhập của bạn đã hết hạn — vui lòng nhấn Tiếp tục lại.", "fa": "ورود شما منقضی شده است — لطفاً دوباره روی ادامه بزنید", "th": "การเข้าสู่ระบบของคุณหมดอายุ — โปรดแตะดำเนินการต่ออีกครั้ง"
};

NOEL_I18N["class.details_failed"] = {
  "en": "Your details could not be saved. Please try again.", "es": "No se pudieron guardar tus datos. Inténtalo de nuevo.", "fr": "Vos coordonnées n'ont pas pu être enregistrées. Veuillez réessayer.", "ar": "تعذّر حفظ بياناتك. يرجى المحاولة مرة أخرى.",
  "pt": "Não foi possível salvar seus dados. Tente novamente.", "ur": "Aapki details save nahi ho saki. Dobara try karen.", "hi": "आपका विवरण सहेजा नहीं जा सका। कृपया फिर से प्रयास करें।", "bn": "আপনার বিবরণ সংরক্ষণ করা যায়নি। আবার চেষ্টা করুন।",
  "ud": "آپ کی تفصیلات محفوظ نہیں ہو سکیں، براہ کرم دوبارہ کوشش کریں", "zh": "无法保存您的信息。请重试。", "de": "Ihre Daten konnten nicht gespeichert werden. Bitte versuchen Sie es erneut.", "it": "Non è stato possibile salvare i tuoi dati. Riprova.",
  "ru": "Не удалось сохранить ваши данные. Пожалуйста, попробуйте снова.", "tr": "Bilgileriniz kaydedilemedi. Lütfen tekrar deneyin.", "ko": "정보를 저장할 수 없습니다. 다시 시도해 주세요.", "ja": "詳細を保存できませんでした。もう一度お試しください。",
  "vi": "Không thể lưu thông tin của bạn. Vui lòng thử lại.", "fa": "جزئیات شما ذخیره نشد، لطفاً دوباره تلاش کنید", "th": "ไม่สามารถบันทึกรายละเอียดของคุณได้ โปรดลองอีกครั้ง"
};

NOEL_I18N["class.select_failed"] = {
  "en": "That class could not be selected. Please try again.", "es": "No se pudo seleccionar esa clase. Inténtalo de nuevo.", "fr": "Cette classe n'a pas pu être sélectionnée. Veuillez réessayer.", "ar": "تعذّر اختيار هذه الفئة. يرجى المحاولة مرة أخرى.",
  "pt": "Não foi possível selecionar essa classe. Tente novamente.", "ur": "Wo class select nahi ho saki. Dobara try karen.", "hi": "वह श्रेणी चुनी नहीं जा सकी। कृपया फिर से प्रयास करें।", "bn": "সেই শ্রেণিটি নির্বাচন করা যায়নি। আবার চেষ্টা করুন।",
  "ud": "یہ کلاس منتخب نہیں ہو سکی، براہ کرم دوبارہ کوشش کریں", "zh": "无法选择该级别。请重试。", "de": "Diese Klasse konnte nicht ausgewählt werden. Bitte versuchen Sie es erneut.", "it": "Non è stato possibile selezionare questa classe. Riprova.",
  "ru": "Не удалось выбрать этот класс. Пожалуйста, попробуйте снова.", "tr": "Bu sınıf seçilemedi. Lütfen tekrar deneyin.", "ko": "이 클래스를 선택할 수 없습니다. 다시 시도해 주세요.", "ja": "このクラスを選択できませんでした。もう一度お試しください。",
  "vi": "Không thể chọn hạng này. Vui lòng thử lại.", "fa": "این کلاس انتخاب نشد، لطفاً دوباره تلاش کنید", "th": "ไม่สามารถเลือกระดับนี้ได้ โปรดลองอีกครั้ง"
};

NOEL_I18N["class.signin_failed"] = {
  "en": "Sign-in did not work. Please try again.", "es": "El inicio de sesión no funcionó. Inténtalo de nuevo.", "fr": "La connexion n'a pas fonctionné. Veuillez réessayer.", "ar": "لم ينجح تسجيل الدخول. يرجى المحاولة مرة أخرى.",
  "pt": "O login não funcionou. Tente novamente.", "ur": "Sign-in kaam nahi kiya. Dobara try karen.", "hi": "साइन-इन काम नहीं किया। कृपया फिर से प्रयास करें।", "bn": "সাইন-ইন কাজ করেনি। আবার চেষ্টা করুন।",
  "ud": "سائن ان ناکام رہا، براہ کرم دوبارہ کوشش کریں", "zh": "登录失败。请重试。", "de": "Die Anmeldung hat nicht funktioniert. Bitte versuchen Sie es erneut.", "it": "L'accesso non ha funzionato. Riprova.",
  "ru": "Вход не удался. Пожалуйста, попробуйте снова.", "tr": "Giriş yapılamadı. Lütfen tekrar deneyin.", "ko": "로그인에 실패했습니다. 다시 시도해 주세요.", "ja": "サインインできませんでした。もう一度お試しください。",
  "vi": "Đăng nhập không thành công. Vui lòng thử lại.", "fa": "ورود ناموفق بود، لطفاً دوباره تلاش کنید", "th": "เข้าสู่ระบบไม่สำเร็จ โปรดลองอีกครั้ง"
};

NOEL_I18N["class.unreachable"] = {
  "en": "Could not reach the booking service. Please try again.", "es": "No se pudo contactar con el servicio de reservas. Inténtalo de nuevo.", "fr": "Impossible de joindre le service de réservation. Veuillez réessayer.", "ar": "تعذّر الوصول إلى خدمة الحجز. يرجى المحاولة مرة أخرى.",
  "pt": "Não foi possível acessar o serviço de reservas. Tente novamente.", "ur": "Booking service se rabta nahi ho saka. Dobara try karen.", "hi": "बुकिंग सेवा से संपर्क नहीं हो सका। कृपया फिर से प्रयास करें।", "bn": "বুকিং পরিষেবার সঙ্গে যোগাযোগ করা যায়নি। আবার চেষ্টা করুন।",
  "ud": "بکنگ سروس تک نہیں پہنچا جا سکا، براہ کرم دوبارہ کوشش کریں", "zh": "无法连接到预订服务。请重试。", "de": "Der Buchungsdienst konnte nicht erreicht werden. Bitte versuchen Sie es erneut.", "it": "Non è stato possibile raggiungere il servizio di prenotazione. Riprova.",
  "ru": "Не удалось связаться со службой бронирования. Пожалуйста, попробуйте снова.", "tr": "Rezervasyon hizmetine ulaşılamadı. Lütfen tekrar deneyin.", "ko": "예약 서비스에 연결할 수 없습니다. 다시 시도해 주세요.", "ja": "予約サービスに接続できませんでした。もう一度お試しください。",
  "vi": "Không thể kết nối đến dịch vụ đặt xe. Vui lòng thử lại.", "fa": "نمی‌توان به سرویس رزرو رسید، لطفاً دوباره تلاش کنید", "th": "ไม่สามารถติดต่อบริการจองได้ โปรดลองอีกครั้ง"
};

NOEL_I18N["class.unreachable_conn"] = {
  "en": "Could not reach the booking service. Please check your connection and try again.", "es": "No se pudo contactar con el servicio de reservas. Revisa tu conexión e inténtalo de nuevo.", "fr": "Impossible de joindre le service de réservation. Vérifiez votre connexion et réessayez.", "ar": "تعذّر الوصول إلى خدمة الحجز. يرجى التحقق من اتصالك والمحاولة مرة أخرى.",
  "pt": "Não foi possível acessar o serviço de reservas. Verifique sua conexão e tente novamente.", "ur": "Booking service se rabta nahi ho saka. Apna connection check karke dobara try karen.", "hi": "बुकिंग सेवा से संपर्क नहीं हो सका। कृपया अपना कनेक्शन जाँचें और फिर से प्रयास करें।", "bn": "বুকিং পরিষেবার সঙ্গে যোগাযোগ করা যায়নি। আপনার সংযোগ দেখে আবার চেষ্টা করুন।",
  "ud": "بکنگ سروس تک نہیں پہنچا جا سکا، براہ کرم اپنا کنکشن چیک کریں اور دوبارہ کوشش کریں", "zh": "无法连接到预订服务。请检查您的网络连接并重试。", "de": "Der Buchungsdienst konnte nicht erreicht werden. Bitte überprüfen Sie Ihre Verbindung und versuchen Sie es erneut.", "it": "Non è stato possibile raggiungere il servizio di prenotazione. Controlla la connessione e riprova.",
  "ru": "Не удалось связаться со службой бронирования. Пожалуйста, проверьте соединение и попробуйте снова.", "tr": "Rezervasyon hizmetine ulaşılamadı. Lütfen bağlantınızı kontrol edip tekrar deneyin.", "ko": "예약 서비스에 연결할 수 없습니다. 연결을 확인한 뒤 다시 시도해 주세요.", "ja": "予約サービスに接続できませんでした。接続を確認して、もう一度お試しください。",
  "vi": "Không thể kết nối đến dịch vụ đặt xe. Vui lòng kiểm tra kết nối của bạn và thử lại.", "fa": "نمی‌توان به سرویس رزرو رسید، لطفاً اتصال خود را بررسی کنید و دوباره تلاش کنید", "th": "ไม่สามารถติดต่อบริการจองได้ โปรดตรวจสอบการเชื่อมต่อของคุณแล้วลองอีกครั้ง"
};

NOEL_I18N["class.wrong"] = {
  "en": "Something went wrong. Please try again.", "es": "Algo salió mal. Inténtalo de nuevo.", "fr": "Une erreur s'est produite. Veuillez réessayer.", "ar": "حدث خطأ ما. يرجى المحاولة مرة أخرى.",
  "pt": "Algo deu errado. Tente novamente.", "ur": "Kuch ghalat ho gaya. Dobara try karen.", "hi": "कुछ गलत हो गया। कृपया फिर से प्रयास करें।", "bn": "কিছু ভুল হয়েছে। আবার চেষ্টা করুন।",
  "ud": "کچھ غلط ہوا، براہ کرم دوبارہ کوشش کریں", "zh": "出了点问题。请重试。", "de": "Etwas ist schiefgelaufen. Bitte versuchen Sie es erneut.", "it": "Qualcosa è andato storto. Riprova.",
  "ru": "Что-то пошло не так. Пожалуйста, попробуйте снова.", "tr": "Bir şeyler ters gitti. Lütfen tekrar deneyin.", "ko": "문제가 발생했습니다. 다시 시도해 주세요.", "ja": "問題が発生しました。もう一度お試しください。",
  "vi": "Đã xảy ra lỗi. Vui lòng thử lại.", "fa": "مشکلی پیش آمد، لطفاً دوباره تلاش کنید", "th": "เกิดข้อผิดพลาด โปรดลองอีกครั้ง"
};

NOEL_I18N["status.finding"] = {
  "en": "Finding your chauffeur…", "es": "Buscando tu chófer…", "fr": "Recherche de votre chauffeur…", "ar": "جارٍ البحث عن سائقك…",
  "pt": "Procurando seu motorista…", "ur": "Aapka chauffeur dhoondha ja raha hai…", "hi": "आपका शॉफ़र खोजा जा रहा है…", "bn": "আপনার শোফার খোঁজা হচ্ছে…",
  "ud": "آپ کے لیے ڈرائیور تلاش کیا جا رہا ہے…", "zh": "正在为您寻找司机…", "de": "Ihr Chauffeur wird gesucht…", "it": "Ricerca del tuo chauffeur…",
  "ru": "Поиск вашего шофёра…", "tr": "Şoförünüz aranıyor…", "ko": "쇼퍼를 찾고 있습니다…", "ja": "ショファーを探しています…",
  "vi": "Đang tìm tài xế cho bạn…", "fa": "در حال یافتن راننده برای شما…", "th": "กำลังหาคนขับให้คุณ…"
};

NOEL_I18N["status.request_with_us"] = {
  "en": "Your request is with us. Please keep this page open.", "es": "Tu solicitud está con nosotros. Mantén esta página abierta.", "fr": "Votre demande est bien reçue. Veuillez garder cette page ouverte.", "ar": "طلبك لدينا. يرجى إبقاء هذه الصفحة مفتوحة.",
  "pt": "Sua solicitação está conosco. Mantenha esta página aberta.", "ur": "Aapki request hamare paas hai. Ye page khula rakhen.", "hi": "आपका अनुरोध हमारे पास है। कृपया यह पेज खुला रखें।", "bn": "আপনার অনুরোধ আমাদের কাছে আছে। এই পাতাটি খোলা রাখুন।",
  "ud": "آپ کی درخواست ہمارے پاس ہے، براہ کرم یہ صفحہ کھلا رکھیں", "zh": "您的请求已收到。请保持此页面打开。", "de": "Ihre Anfrage liegt uns vor. Bitte lassen Sie diese Seite geöffnet.", "it": "La tua richiesta è con noi. Tieni aperta questa pagina.",
  "ru": "Ваш запрос у нас. Пожалуйста, держите эту страницу открытой.", "tr": "İsteğiniz bize ulaştı. Lütfen bu sayfayı açık tutun.", "ko": "요청이 접수되었습니다. 이 페이지를 열어 두세요.", "ja": "リクエストを受け取りました。このページを開いたままにしてください。",
  "vi": "Yêu cầu của bạn đã được nhận. Vui lòng giữ trang này mở.", "fa": "درخواست شما نزد ماست، لطفاً این صفحه را باز نگه دارید", "th": "คำขอของคุณอยู่กับเรา โปรดเปิดหน้านี้ไว้"
};

NOEL_I18N["status.confirmed"] = {
  "en": "Your chauffeur is confirmed", "es": "Tu chófer está confirmado", "fr": "Votre chauffeur est confirmé", "ar": "تم تأكيد سائقك",
  "pt": "Seu motorista está confirmado", "ur": "Aapka chauffeur confirm ho gaya", "hi": "आपका शॉफ़र कन्फ़र्म हो गया", "bn": "আপনার শোফার নিশ্চিত হয়েছে",
  "ud": "آپ کے ڈرائیور کی تصدیق ہو گئی", "zh": "您的司机已确认", "de": "Ihr Chauffeur ist bestätigt", "it": "Il tuo chauffeur è confermato",
  "ru": "Ваш шофёр подтверждён", "tr": "Şoförünüz onaylandı", "ko": "쇼퍼가 확인되었습니다", "ja": "ショファーが確認されました",
  "vi": "Tài xế của bạn đã được xác nhận", "fa": "رانندهٔ شما تأیید شد", "th": "ยืนยันคนขับของคุณแล้ว"
};

NOEL_I18N["status.on_the_way"] = {
  "en": "Your chauffeur is on the way.", "es": "Tu chófer está en camino.", "fr": "Votre chauffeur est en route.", "ar": "سائقك في الطريق إليك.",
  "pt": "Seu motorista está a caminho.", "ur": "Aapka chauffeur raaste mein hai.", "hi": "आपका शॉफ़र रास्ते में है।", "bn": "আপনার শোফার পথে আছেন।",
  "ud": "آپ کا ڈرائیور آ رہا ہے", "zh": "您的司机正在路上。", "de": "Ihr Chauffeur ist auf dem Weg.", "it": "Il tuo chauffeur è in arrivo.",
  "ru": "Ваш шофёр в пути.", "tr": "Şoförünüz yolda.", "ko": "쇼퍼가 오는 중입니다.", "ja": "ショファーが向かっています。",
  "vi": "Tài xế của bạn đang trên đường.", "fa": "رانندهٔ شما در راه است", "th": "คนขับของคุณกำลังมา"
};

NOEL_I18N["status.details_sent"] = {
  "en": "These details were also sent to your phone and email.", "es": "Estos datos también se enviaron a tu teléfono y correo electrónico.", "fr": "Ces informations ont également été envoyées sur votre téléphone et par e-mail.", "ar": "تم إرسال هذه التفاصيل أيضًا إلى هاتفك وبريدك الإلكتروني.",
  "pt": "Esses dados também foram enviados para seu telefone e e-mail.", "ur": "Ye details aapke phone aur email par bhi bheji gayi hain.", "hi": "ये जानकारी आपके फ़ोन और ईमेल पर भी भेजी गई है।", "bn": "এই বিবরণ আপনার ফোন ও ইমেইলেও পাঠানো হয়েছে।",
  "ud": "یہ تفصیلات آپ کے فون اور ای میل پر بھی بھیجی گئی ہیں", "zh": "这些信息也已发送到您的手机和邮箱。", "de": "Diese Daten wurden auch an Ihr Telefon und Ihre E-Mail-Adresse gesendet.", "it": "Questi dati sono stati inviati anche al tuo telefono e alla tua email.",
  "ru": "Эти данные также были отправлены на ваш телефон и электронную почту.", "tr": "Bu bilgiler telefonunuza ve e-postanıza da gönderildi.", "ko": "이 정보는 휴대폰과 이메일로도 전송되었습니다.", "ja": "これらの詳細はお客様の電話とメールにも送信されました。",
  "vi": "Các thông tin này cũng đã được gửi đến điện thoại và email của bạn.", "fa": "این جزئیات به تلفن و ایمیل شما نیز ارسال شده است", "th": "รายละเอียดเหล่านี้ถูกส่งไปยังโทรศัพท์และอีเมลของคุณด้วย"
};

NOEL_I18N["status.on_the_way_heading"] = {
  "en": "Your chauffeur on the way", "es": "Tu chófer en camino", "fr": "Votre chauffeur en route", "ar": "سائقك في الطريق",
  "pt": "Seu motorista a caminho", "ur": "Aapka chauffeur raaste mein", "hi": "आपका शॉफ़र रास्ते में", "bn": "আপনার শোফার পথে",
  "ud": "آپ کا ڈرائیور آ رہا ہے", "zh": "您的司机正在路上", "de": "Ihr Chauffeur ist auf dem Weg", "it": "Il tuo chauffeur è in arrivo",
  "ru": "Ваш шофёр в пути", "tr": "Şoförünüz yolda", "ko": "쇼퍼가 오는 중입니다", "ja": "ショファーが向かっています",
  "vi": "Tài xế của bạn đang trên đường", "fa": "رانندهٔ شما در راه است", "th": "คนขับของคุณกำลังมา"
};

NOEL_I18N["status.total_ready"] = {
  "en": "Your total is ready", "es": "Tu total está listo", "fr": "Votre total est prêt", "ar": "المجموع جاهز",
  "pt": "Seu total está pronto", "ur": "Aapka total ready hai", "hi": "आपका कुल तैयार है", "bn": "আপনার মোট তৈরি",
  "ud": "آپ کا کل تیار ہے", "zh": "您的总价已就绪", "de": "Ihr Gesamtpreis ist fertig", "it": "Il tuo totale è pronto",
  "ru": "Ваша общая стоимость готова", "tr": "Toplamınız hazır", "ko": "총액이 준비되었습니다", "ja": "合計が準備できました",
  "vi": "Tổng giá của bạn đã sẵn sàng", "fa": "مجموع شما آماده است", "th": "ยอดรวมของคุณพร้อมแล้ว"
};

NOEL_I18N["status.pay_below"] = {
  "en": "Please pay by card below — your chauffeur will be assigned right after payment.", "es": "Paga con tarjeta abajo: tu chófer será asignado justo después del pago.", "fr": "Veuillez payer par carte ci-dessous — votre chauffeur sera assigné juste après le paiement.", "ar": "يرجى الدفع بالبطاقة أدناه — وسيتم تعيين سائقك مباشرة بعد الدفع.",
  "pt": "Pague com cartão abaixo — seu motorista será designado logo após o pagamento.", "ur": "Neeche card se pay karen — payment ke foran baad aapka chauffeur assign ho jayega.", "hi": "कृपया नीचे कार्ड से भुगतान करें — भुगतान के तुरंत बाद आपका शॉफ़र नियुक्त हो जाएगा।", "bn": "নিচে কার্ড দিয়ে পেমেন্ট করুন — পেমেন্টের পরপরই আপনার শোফার নিয়োগ করা হবে।",
  "ud": "براہ کرم نیچے کارڈ سے ادائیگی کریں — ادائیگی کے فوراً بعد آپ کا ڈرائیور مقرر ہو جائے گا", "zh": "请在下方用卡支付——付款后将立即为您指派司机。", "de": "Bitte bezahlen Sie unten per Karte — Ihr Chauffeur wird direkt nach der Zahlung zugewiesen.", "it": "Paga con carta qui sotto — il tuo chauffeur verrà assegnato subito dopo il pagamento.",
  "ru": "Пожалуйста, оплатите картой ниже — ваш шофёр будет назначен сразу после оплаты.", "tr": "Lütfen aşağıdan kartla ödeyin — şoförünüz ödemeden hemen sonra atanacaktır.", "ko": "아래에서 카드로 결제해 주세요. 결제 후 바로 쇼퍼가 배정됩니다.", "ja": "以下でカードでお支払いください。お支払い後すぐにショファーが割り当てられます。",
  "vi": "Vui lòng thanh toán bằng thẻ bên dưới — tài xế của bạn sẽ được chỉ định ngay sau khi thanh toán.", "fa": "لطفاً در زیر با کارت پرداخت کنید — رانندهٔ شما بلافاصله پس از پرداخت تعیین می‌شود", "th": "โปรดชำระเงินด้วยบัตรด้านล่าง — คนขับของคุณจะได้รับมอบหมายทันทีหลังชำระเงิน"
};

NOEL_I18N["status.your_total"] = {
  "en": "Your total", "es": "Tu total", "fr": "Votre total", "ar": "المجموع الخاص بك",
  "pt": "Seu total", "ur": "Aapka total", "hi": "आपका कुल", "bn": "আপনার মোট",
  "ud": "آپ کا کل", "zh": "您的总价", "de": "Ihr Gesamtpreis", "it": "Il tuo totale",
  "ru": "Ваша общая стоимость", "tr": "Toplamınız", "ko": "합계", "ja": "お客様の合計",
  "vi": "Tổng giá của bạn", "fa": "مجموع شما", "th": "ยอดรวมของคุณ"
};

NOEL_I18N["status.one_total"] = {
  "en": "One single total for your ride. No breakdown, no hidden charges.", "es": "Un solo total para tu viaje. Sin desglose ni cargos ocultos.", "fr": "Un seul total pour votre trajet. Aucun détail, aucun frais caché.", "ar": "مجموع واحد لرحلتك. لا تفصيل ولا رسوم خفية.",
  "pt": "Um único total para sua viagem. Sem detalhamento, sem taxas ocultas.", "ur": "Aapki ride ka ek hi total. Na breakdown, na chhupe hue charges.", "hi": "आपकी सवारी का एक ही कुल। कोई विवरण नहीं, कोई छिपा शुल्क नहीं।", "bn": "আপনার রাইডের একটাই মোট। কোনো বিবরণ নেই, কোনো লুকানো চার্জ নেই।",
  "ud": "آپ کی سواری کے لیے ایک کل رقم، کوئی تفصیل نہیں، کوئی پوشیدہ چارج نہیں", "zh": "您的行程只有一个总价。无明细，无隐藏费用。", "de": "Ein einziger Gesamtpreis für Ihre Fahrt. Keine Aufschlüsselung, keine versteckten Kosten.", "it": "Un unico totale per la tua corsa. Nessun dettaglio, nessun costo nascosto.",
  "ru": "Одна общая стоимость вашей поездки. Без разбивки, без скрытых платежей.", "tr": "Yolculuğunuz için tek bir toplam. Döküm yok, gizli ücret yok.", "ko": "이동에 대한 단일 총액입니다. 내역도, 숨은 요금도 없습니다.", "ja": "乗車の合計は1つだけです。内訳も隠れた料金もありません。",
  "vi": "Một tổng giá duy nhất cho chuyến đi của bạn. Không chi tiết, không phí ẩn.", "fa": "یک مجموع برای سفر شما، بدون جزئیات، بدون هزینهٔ پنهان", "th": "ยอดรวมเดียวสำหรับการเดินทางของคุณ ไม่มีการแยกย่อย ไม่มีค่าใช้จ่ายแอบแฝง"
};

NOEL_I18N["status.pay_by_card"] = {
  "en": "Pay by card", "es": "Pagar con tarjeta", "fr": "Payer par carte", "ar": "ادفع بالبطاقة",
  "pt": "Pagar com cartão", "ur": "Card se pay karen", "hi": "कार्ड से भुगतान करें", "bn": "কার্ড দিয়ে পেমেন্ট করুন",
  "ud": "کارڈ سے ادائیگی کریں", "zh": "用卡支付", "de": "Per Karte bezahlen", "it": "Paga con carta",
  "ru": "Оплатить картой", "tr": "Kartla öde", "ko": "카드로 결제", "ja": "カードで支払う",
  "vi": "Thanh toán bằng thẻ", "fa": "پرداخت با کارت", "th": "ชำระเงินด้วยบัตร"
};

NOEL_I18N["status.card_unavailable"] = {
  "en": "Card payments are not set up yet. Please try again later.", "es": "Los pagos con tarjeta aún no están configurados. Inténtalo más tarde.", "fr": "Les paiements par carte ne sont pas encore configurés. Veuillez réessayer plus tard.", "ar": "الدفع بالبطاقة غير مُعدّ بعد. يرجى المحاولة لاحقًا.",
  "pt": "Pagamentos com cartão ainda não estão configurados. Tente novamente mais tarde.", "ur": "Card payments abhi set nahi hain. Thodi der mein dobara try karen.", "hi": "कार्ड भुगतान अभी सेट नहीं है। कृपया बाद में फिर से प्रयास करें।", "bn": "কার্ড পেমেন্ট এখনো চালু হয়নি। পরে আবার চেষ্টা করুন।",
  "ud": "کارڈ سے ادائیگی ابھی سیٹ اپ نہیں ہوئی ہے، براہ کرم بعد میں دوبارہ کوشش کریں", "zh": "卡支付尚未设置。请稍后再试。", "de": "Kartenzahlungen sind noch nicht eingerichtet. Bitte versuchen Sie es später erneut.", "it": "I pagamenti con carta non sono ancora attivi. Riprova più tardi.",
  "ru": "Оплата картой пока не настроена. Пожалуйста, попробуйте позже.", "tr": "Kart ödemeleri henüz kurulmadı. Lütfen daha sonra tekrar deneyin.", "ko": "카드 결제가 아직 설정되지 않았습니다. 나중에 다시 시도해 주세요.", "ja": "カード決済はまだ設定されていません。後でもう一度お試しください。",
  "vi": "Thanh toán bằng thẻ chưa được thiết lập. Vui lòng thử lại sau.", "fa": "پرداخت با کارت هنوز راه‌اندازی نشده است، لطفاً بعداً دوباره تلاش کنید", "th": "ยังไม่ได้ตั้งค่าการชำระเงินด้วยบัตร โปรดลองอีกครั้งในภายหลัง"
};

NOEL_I18N["status.loading_payment"] = {
  "en": "Loading secure payment…", "es": "Cargando el pago seguro…", "fr": "Chargement du paiement sécurisé…", "ar": "جارٍ تحميل الدفع الآمن…",
  "pt": "Carregando pagamento seguro…", "ur": "Secure payment load ho raha hai…", "hi": "सुरक्षित भुगतान लोड हो रहा है…", "bn": "নিরাপদ পেমেন্ট লোড হচ্ছে…",
  "ud": "محفوظ ادائیگی لوڈ ہو رہی ہے…", "zh": "正在加载安全支付…", "de": "Sichere Zahlung wird geladen…", "it": "Caricamento del pagamento sicuro…",
  "ru": "Загрузка безопасной оплаты…", "tr": "Güvenli ödeme yükleniyor…", "ko": "안전 결제를 불러오는 중…", "ja": "安全な決済を読み込み中…",
  "vi": "Đang tải thanh toán an toàn…", "fa": "در حال بارگذاری پرداخت امن…", "th": "กำลังโหลดการชำระเงินที่ปลอดภัย…"
};

NOEL_I18N["status.test_mode"] = {
  "en": "TEST MODE — no real charge.", "es": "MODO DE PRUEBA: sin cargo real.", "fr": "MODE TEST — aucun débit réel.", "ar": "وضع الاختبار — لا يوجد خصم حقيقي.",
  "pt": "MODO DE TESTE — sem cobrança real.", "ur": "TEST MODE — koi real charge nahi.", "hi": "टेस्ट मोड — कोई असली शुल्क नहीं।", "bn": "টেস্ট মোড — কোনো আসল চার্জ নেই।",
  "ud": "ٹیسٹ موڈ — کوئی حقیقی چارج نہیں", "zh": "测试模式——不收取实际费用。", "de": "TESTMODUS — keine echte Abbuchung.", "it": "MODALITÀ TEST — nessun addebito reale.",
  "ru": "ТЕСТОВЫЙ РЕЖИМ — реальная оплата не списывается.", "tr": "TEST MODU — gerçek ücret alınmaz.", "ko": "테스트 모드 — 실제 요금이 청구되지 않습니다.", "ja": "テストモード — 実際の請求はありません。",
  "vi": "CHẾ ĐỘ THỬ NGHIỆM — không tính phí thật.", "fa": "حالت آزمایشی — هیچ هزینهٔ واقعی نیست", "th": "โหมดทดสอบ — ไม่มีการเรียกเก็บเงินจริง"
};

NOEL_I18N["status.test_note"] = {
  "en": "This payment form is in test mode. No real payment will be taken from your card.", "es": "Este formulario de pago está en modo de prueba. No se cobrará nada real de tu tarjeta.", "fr": "Ce formulaire de paiement est en mode test. Aucun paiement réel ne sera prélevé sur votre carte.", "ar": "نموذج الدفع هذا في وضع الاختبار. لن يتم خصم أي مبلغ حقيقي من بطاقتك.",
  "pt": "Este formulário de pagamento está em modo de teste. Nenhum pagamento real será cobrado do seu cartão.", "ur": "Ye payment form test mode mein hai. Aapke card se koi real payment nahi liya jayega.", "hi": "यह भुगतान फ़ॉर्म टेस्ट मोड में है। आपके कार्ड से कोई असली भुगतान नहीं लिया जाएगा।", "bn": "এই পেমেন্ট ফর্মটি টেস্ট মোডে আছে। আপনার কার্ড থেকে কোনো আসল পেমেন্ট নেওয়া হবে না।",
  "ud": "یہ ادائیگی فارم ٹیسٹ موڈ میں ہے۔ آپ کے کارڈ سے کوئی حقیقی چارج نہیں لیا جائے گا", "zh": "此支付表单处于测试模式。不会从您的卡中收取实际付款。", "de": "Dieses Zahlungsformular befindet sich im Testmodus. Von Ihrer Karte wird keine echte Zahlung abgebucht.", "it": "Questo modulo di pagamento è in modalità test. Non verrà effettuato alcun pagamento reale dalla tua carta.",
  "ru": "Эта форма оплаты работает в тестовом режиме. С вашей карты не будет списан реальный платёж.", "tr": "Bu ödeme formu test modundadır. Kartınızdan gerçek bir ödeme alınmayacaktır.", "ko": "이 결제 양식은 테스트 모드입니다. 카드에서 실제 결제가 이루어지지 않습니다.", "ja": "この決済フォームはテストモードです。お客様のカードから実際の支払いは行われません。",
  "vi": "Biểu mẫu thanh toán này đang ở chế độ thử nghiệm. Sẽ không có khoản thanh toán thật nào được trừ từ thẻ của bạn.", "fa": "این فرم پرداخت در حالت آزمایشی است. هیچ هزینهٔ واقعی از کارت شما کسر نمی‌شود", "th": "แบบฟอร์มการชำระเงินนี้อยู่ในโหมดทดสอบ จะไม่มีการเรียกเก็บเงินจริงจากบัตรของคุณ"
};

NOEL_I18N["status.card_name"] = {
  "en": "Name on card", "es": "Nombre en la tarjeta", "fr": "Nom sur la carte", "ar": "الاسم على البطاقة",
  "pt": "Nome no cartão", "ur": "Card par naam", "hi": "कार्ड पर नाम", "bn": "কার্ডে নাম",
  "ud": "کارڈ پر نام", "zh": "持卡人姓名", "de": "Name auf der Karte", "it": "Nome sulla carta",
  "ru": "Имя на карте", "tr": "Karttaki ad", "ko": "카드 명의", "ja": "カード名義",
  "vi": "Tên trên thẻ", "fa": "نام روی کارت", "th": "ชื่อบนบัตร"
};

NOEL_I18N["status.card_number"] = {
  "en": "Card number", "es": "Número de tarjeta", "fr": "Numéro de carte", "ar": "رقم البطاقة",
  "pt": "Número do cartão", "ur": "Card number", "hi": "कार्ड नंबर", "bn": "কার্ড নম্বর",
  "ud": "کارڈ نمبر", "zh": "卡号", "de": "Kartennummer", "it": "Numero di carta",
  "ru": "Номер карты", "tr": "Kart numarası", "ko": "카드 번호", "ja": "カード番号",
  "vi": "Số thẻ", "fa": "شمارهٔ کارت", "th": "หมายเลขบัตร"
};

NOEL_I18N["status.expiry"] = {
  "en": "Expiry (MM/YY)", "es": "Vencimiento (MM/AA)", "fr": "Expiration (MM/AA)", "ar": "تاريخ الانتهاء (شهر/سنة)",
  "pt": "Validade (MM/AA)", "ur": "Expiry (MM/YY)", "hi": "समाप्ति (माह/वर्ष)", "bn": "মেয়াদ (মাস/বছর)",
  "ud": "ختم ہونے کی تاریخ (مہینہ/سال)", "zh": "有效期（月/年）", "de": "Gültig bis (MM/JJ)", "it": "Scadenza (MM/AA)",
  "ru": "Срок действия (ММ/ГГ)", "tr": "Son kullanma (AA/YY)", "ko": "만료일(월/년)", "ja": "有効期限（月/年）",
  "vi": "Ngày hết hạn (MM/YY)", "fa": "تاریخ انقضا (ماه/سال)", "th": "วันหมดอายุ (เดือน/ปี)"
};

NOEL_I18N["status.cvc"] = {
  "en": "CVC", "es": "CVC", "fr": "CVC", "ar": "رمز الأمان",
  "pt": "CVC", "ur": "CVC", "hi": "CVC", "bn": "CVC",
  "ud": "CVC", "zh": "CVC", "de": "CVC", "it": "CVC",
  "ru": "CVC", "tr": "CVC", "ko": "CVC", "ja": "CVC",
  "vi": "CVC", "fa": "CVC", "th": "CVC"
};

NOEL_I18N["status.invoice"] = {
  "en": "Your invoice", "es": "Tu factura", "fr": "Votre facture", "ar": "فاتورتك",
  "pt": "Sua fatura", "ur": "Aapka invoice", "hi": "आपका चालान", "bn": "আপনার চালান",
  "ud": "آپ کا انوائس", "zh": "您的发票", "de": "Ihre Rechnung", "it": "La tua fattura",
  "ru": "Ваш счёт", "tr": "Faturanız", "ko": "청구서", "ja": "請求書",
  "vi": "Hóa đơn của bạn", "fa": "فاکتور شما", "th": "ใบแจ้งหนี้ของคุณ"
};

NOEL_I18N["status.ride_total"] = {
  "en": "Ride total", "es": "Total del viaje", "fr": "Total du trajet", "ar": "إجمالي الرحلة",
  "pt": "Total da viagem", "ur": "Ride total", "hi": "सवारी का कुल", "bn": "রাইডের মোট",
  "ud": "سواری کا کل", "zh": "行程总计", "de": "Fahrt Gesamtpreis", "it": "Totale della corsa",
  "ru": "Итого за поездку", "tr": "Yolculuk toplamı", "ko": "이동 합계", "ja": "乗車合計",
  "vi": "Tổng chuyến đi", "fa": "مجموع سفر", "th": "ยอดรวมการเดินทาง"
};

NOEL_I18N["status.waiting"] = {
  "en": "Waiting charge", "es": "Cargo por espera", "fr": "Frais d'attente", "ar": "رسوم الانتظار",
  "pt": "Taxa de espera", "ur": "Waiting charge", "hi": "प्रतीक्षा शुल्क", "bn": "অপেক্ষার চার্জ",
  "ud": "انتظار کا چارج", "zh": "等候费", "de": "Wartegebühr", "it": "Supplemento di attesa",
  "ru": "Плата за ожидание", "tr": "Bekleme ücreti", "ko": "대기 요금", "ja": "待ち料金",
  "vi": "Phí chờ", "fa": "هزینهٔ انتظار", "th": "ค่ารอ"
};

NOEL_I18N["status.extra_distance"] = {
  "en": "Extra distance", "es": "Distancia extra", "fr": "Distance supplémentaire", "ar": "مسافة إضافية",
  "pt": "Distância extra", "ur": "Extra distance", "hi": "अतिरिक्त दूरी", "bn": "অতিরিক্ত দূরত্ব",
  "ud": "اضافی فاصلہ", "zh": "额外里程", "de": "Zusätzliche Strecke", "it": "Distanza extra",
  "ru": "Дополнительное расстояние", "tr": "Ek mesafe", "ko": "추가 거리", "ja": "追加距離",
  "vi": "Quãng đường thêm", "fa": "مسافت اضافی", "th": "ระยะทางเพิ่มเติม"
};

NOEL_I18N["status.amount_paid"] = {
  "en": "Amount paid", "es": "Cantidad pagada", "fr": "Montant payé", "ar": "المبلغ المدفوع",
  "pt": "Valor pago", "ur": "Amount paid", "hi": "भुगतान की गई राशि", "bn": "পরিশোধিত অর্থ",
  "ud": "ادا شدہ رقم", "zh": "已付金额", "de": "Bezahlter Betrag", "it": "Importo pagato",
  "ru": "Оплаченная сумма", "tr": "Ödenen tutar", "ko": "지불 금액", "ja": "支払済み金額",
  "vi": "Số tiền đã thanh toán", "fa": "مبلغ پرداخت‌شده", "th": "จำนวนเงินที่ชำระ"
};

NOEL_I18N["status.invoice_sent"] = {
  "en": "Your invoice has been sent to your phone and email.", "es": "Tu factura se ha enviado a tu teléfono y correo electrónico.", "fr": "Votre facture a été envoyée sur votre téléphone et par e-mail.", "ar": "تم إرسال فاتورتك إلى هاتفك وبريدك الإلكتروني.",
  "pt": "Sua fatura foi enviada para seu telefone e e-mail.", "ur": "Aapka invoice aapke phone aur email par bhej diya gaya hai.", "hi": "आपका चालान आपके फ़ोन और ईमेल पर भेज दिया गया है।", "bn": "আপনার চালান আপনার ফোন ও ইমেইলে পাঠানো হয়েছে।",
  "ud": "آپ کا انوائس آپ کے فون اور ای میل پر بھیج دیا گیا ہے", "zh": "您的发票已发送到您的手机和邮箱。", "de": "Ihre Rechnung wurde an Ihr Telefon und Ihre E-Mail-Adresse gesendet.", "it": "La tua fattura è stata inviata al tuo telefono e alla tua email.",
  "ru": "Ваш счёт был отправлен на ваш телефон и электронную почту.", "tr": "Faturanız telefonunuza ve e-postanıza gönderildi.", "ko": "청구서가 휴대폰과 이메일로 전송되었습니다.", "ja": "請求書はお客様の電話とメールに送信されました。",
  "vi": "Hóa đơn của bạn đã được gửi đến điện thoại và email của bạn.", "fa": "فاکتور شما به تلفن و ایمیل شما ارسال شد", "th": "ใบแจ้งหนี้ของคุณถูกส่งไปยังโทรศัพท์และอีเมลของคุณแล้ว"
};

NOEL_I18N["status.chat_with_chauffeur"] = {
  "en": "Chat with your chauffeur", "es": "Chatea con tu chófer", "fr": "Discutez avec votre chauffeur", "ar": "تحدث مع سائقك",
  "pt": "Converse com seu motorista", "ur": "Apne chauffeur se chat karen", "hi": "अपने शॉफ़र से चैट करें", "bn": "আপনার শোফারের সঙ্গে চ্যাট করুন",
  "ud": "اپنے ڈرائیور سے چیٹ کریں", "zh": "与您的司机聊天", "de": "Chat mit Ihrem Chauffeur", "it": "Chatta con il tuo chauffeur",
  "ru": "Чат с вашим шофёром", "tr": "Şoförünüzle sohbet edin", "ko": "쇼퍼와 채팅", "ja": "ショファーとチャットする",
  "vi": "Trò chuyện với tài xế của bạn", "fa": "با رانندهٔ خود چت کنید", "th": "แชทกับคนขับของคุณ"
};

NOEL_I18N["status.chat_language_label"] = {
  "en": "Language", "es": "Idioma", "fr": "Langue", "ar": "اللغة",
  "pt": "Idioma", "ur": "Language", "hi": "भाषा", "bn": "ভাষা",
  "ud": "زبان", "zh": "语言", "de": "Sprache", "it": "Lingua",
  "ru": "Язык", "tr": "Dil", "ko": "언어", "ja": "言語",
  "vi": "Ngôn ngữ", "fa": "زبان", "th": "ภาษา"
};

NOEL_I18N["status.chat_input_ph"] = {
  "en": "Write a message…", "es": "Escribe un mensaje…", "fr": "Écrivez un message…", "ar": "اكتب رسالة…",
  "pt": "Escreva uma mensagem…", "ur": "Message likhen…", "hi": "संदेश लिखें…", "bn": "বার্তা লিখুন…",
  "ud": "پیغام لکھیں…", "zh": "写消息…", "de": "Nachricht schreiben…", "it": "Scrivi un messaggio…",
  "ru": "Написать сообщение…", "tr": "Bir mesaj yazın…", "ko": "메시지 작성…", "ja": "メッセージを書く…",
  "vi": "Viết tin nhắn…", "fa": "پیام بنویسید…", "th": "เขียนข้อความ…"
};

NOEL_I18N["status.plate"] = {
  "en": "Plate", "es": "Matrícula", "fr": "Plaque", "ar": "اللوحة",
  "pt": "Placa", "ur": "Plate", "hi": "नंबर प्लेट", "bn": "নম্বর প্লেট",
  "ud": "پلیٹ", "zh": "车牌", "de": "Kennzeichen", "it": "Targa",
  "ru": "Номерной знак", "tr": "Plaka", "ko": "번호판", "ja": "ナンバープレート",
  "vi": "Biển số", "fa": "پلاک", "th": "ทะเบียนรถ"
};

NOEL_I18N["status.phone_label"] = {
  "en": "Phone", "es": "Teléfono", "fr": "Téléphone", "ar": "الهاتف",
  "pt": "Telefone", "ur": "Phone", "hi": "फ़ोन", "bn": "ফোন",
  "ud": "فون", "zh": "电话", "de": "Telefon", "it": "Telefono",
  "ru": "Телефон", "tr": "Telefon", "ko": "전화", "ja": "電話",
  "vi": "Điện thoại", "fa": "تلفن", "th": "โทรศัพท์"
};

NOEL_I18N["status.thankyou"] = {
  "en": "Thank you — your ride is booked.", "es": "Gracias, tu viaje está reservado.", "fr": "Merci — votre trajet est réservé.", "ar": "شكرًا لك — تم حجز رحلتك.",
  "pt": "Obrigado — sua viagem está reservada.", "ur": "Shukriya — aapki ride book ho gayi.", "hi": "धन्यवाद — आपकी सवारी बुक हो गई।", "bn": "ধন্যবাদ — আপনার রাইড বুক হয়েছে।",
  "ud": "شکریہ — آپ کی سواری بک ہو گئی ہے", "zh": "谢谢——您的行程已预订。", "de": "Vielen Dank — Ihre Fahrt ist gebucht.", "it": "Grazie — la tua corsa è prenotata.",
  "ru": "Спасибо — ваша поездка забронирована.", "tr": "Teşekkürler — yolculuğunuz rezerve edildi.", "ko": "감사합니다. 이동이 예약되었습니다.", "ja": "ありがとうございます。乗車が予約されました。",
  "vi": "Cảm ơn — chuyến đi của bạn đã được đặt.", "fa": "متشکریم — سفر شما رزرو شد", "th": "ขอบคุณ — การเดินทางของคุณจองแล้ว"
};

NOEL_I18N["status.stripe_hold_note"] = {
  "en": "Your card is charged as a hold when you book. Your card details go directly to Stripe — they are never typed into, or stored on, this site.", "es": "Tu tarjeta se carga como retención al reservar. Los datos de tu tarjeta van directamente a Stripe: nunca se escriben ni se guardan en este sitio.", "fr": "Votre carte est débitée à titre de garantie lors de la réservation. Les données de votre carte vont directement à Stripe — elles ne sont jamais saisies ni stockées sur ce site.", "ar": "يتم خصم مبلغ من بطاقتك كحجز عند الحجز. تذهب بيانات بطاقتك مباشرة إلى Stripe — ولا تُكتب أو تُحفظ أبدًا على هذا الموقع.",
  "pt": "Seu cartão é cobrado como retenção ao reservar. Os dados do seu cartão vão diretamente para a Stripe — nunca são digitados ou armazenados neste site.", "ur": "Book karte waqt aapke card par hold lagaya jata hai. Aapke card ki details seedha Stripe ko jati hain — wo is site par na likhi jati hain na save hoti hain.", "hi": "बुक करते समय आपके कार्ड पर होल्ड लगाया जाता है। आपके कार्ड का विवरण सीधे Stripe को जाता है — यह इस साइट पर न तो लिखा जाता है और न ही सहेजा जाता है।", "bn": "বুক করার সময় আপনার কার্ডে হোল্ড চার্জ করা হয়। আপনার কার্ডের বিবরণ সরাসরি Stripe-এ যায় — এগুলো এই সাইটে কখনো লেখা বা সংরক্ষণ করা হয় না।",
  "ud": "جب آپ بک کریں گے تو آپ کے کارڈ پر ہولڈ لگایا جائے گا۔ آپ کے کارڈ کی تفصیلات براہ راست Stripe کو بھیجی جاتی ہیں — وہ نہ تو اس ویب سائٹ پر ٹائپ کی جاتی ہیں اور نہ ہی محفوظ کی جاتی ہیں", "zh": "预订时您的卡将被预授权扣款。您的卡信息直接发送给 Stripe——绝不会在本网站输入或存储。", "de": "Ihre Karte wird bei der Buchung als Kaution belastet. Ihre Kartendaten gehen direkt an Stripe — sie werden auf dieser Seite weder eingegeben noch gespeichert.", "it": "La tua carta viene addebitata come deposito quando prenoti. I dati della tua carta vanno direttamente a Stripe — non vengono mai digitati né memorizzati su questo sito.",
  "ru": "Ваша карта списывается как залог при бронировании. Данные вашей карты направляются напрямую в Stripe — они никогда не вводятся и не хранятся на этом сайте.", "tr": "Kartınızdan rezervasyon yaparken provizyon alınır. Kart bilgileriniz doğrudan Stripe'a gider — bu siteye hiçbir zaman yazılmaz veya burada saklanmaz.", "ko": "예약 시 카드에 보류 결제가 청구됩니다. 카드 정보는 Stripe으로 직접 전송되며 이 사이트에 입력되거나 저장되지 않습니다.", "ja": "予約時にカードに仮請求がかかります。カード詳細はStripeに直接送信されます。このサイトに入力されたり保存されたりすることは決してありません。",
  "vi": "Thẻ của bạn sẽ bị giữ tiền khi bạn đặt xe. Chi tiết thẻ của bạn được gửi trực tiếp đến Stripe — chúng không bao giờ được nhập vào, hay lưu trữ trên, trang web này.", "fa": "هنگام رزرو، مبلغی روی کارت شما مسدود می‌شود. جزئیات کارت شما مستقیماً به Stripe ارسال می‌شود — در این وب‌سایت نه تایپ و نه ذخیره می‌شود", "th": "บัตรของคุณจะถูกกันวงเงินเมื่อคุณจอง รายละเอียดบัตรของคุณส่งตรงไปยัง Stripe — จะไม่มีการพิมพ์ลงใน หรือจัดเก็บไว้บน เว็บไซต์นี้"
};

NOEL_I18N["status.saved_cards"] = {
  "en": "Your saved cards", "es": "Tus tarjetas guardadas", "fr": "Vos cartes enregistrées", "ar": "بطاقاتك المحفوظة",
  "pt": "Seus cartões salvos", "ur": "Aapke saved cards", "hi": "आपके सहेजे गए कार्ड", "bn": "আপনার সংরক্ষিত কার্ড",
  "ud": "آپ کے محفوظ شدہ کارڈ", "zh": "您保存的卡", "de": "Ihre gespeicherten Karten", "it": "Le tue carte salvate",
  "ru": "Ваши сохранённые карты", "tr": "Kayıtlı kartlarınız", "ko": "저장된 카드", "ja": "保存済みのカード",
  "vi": "Thẻ đã lưu của bạn", "fa": "کارت‌های ذخیره‌شدهٔ شما", "th": "บัตรที่บันทึกไว้ของคุณ"
};

NOEL_I18N["status.card_details"] = {
  "en": "Card details", "es": "Datos de la tarjeta", "fr": "Détails de la carte", "ar": "بيانات البطاقة",
  "pt": "Dados do cartão", "ur": "Card details", "hi": "कार्ड विवरण", "bn": "কার্ডের বিবরণ",
  "ud": "کارڈ کی تفصیلات", "zh": "卡片信息", "de": "Kartendaten", "it": "Dati della carta",
  "ru": "Данные карты", "tr": "Kart bilgileri", "ko": "카드 정보", "ja": "カード詳細",
  "vi": "Chi tiết thẻ", "fa": "جزئیات کارت", "th": "รายละเอียดบัตร"
};

NOEL_I18N["status.save_card"] = {
  "en": "Save this card for future rides", "es": "Guardar esta tarjeta para futuros viajes", "fr": "Enregistrer cette carte pour vos prochains trajets", "ar": "احفظ هذه البطاقة للرحلات القادمة",
  "pt": "Salvar este cartão para viagens futuras", "ur": "Aage ki rides ke liye ye card save karen", "hi": "भविष्य की सवारियों के लिए यह कार्ड सहेजें", "bn": "ভবিষ্যতের রাইডের জন্য এই কার্ড সংরক্ষণ করুন",
  "ud": "یہ کارڈ اگلی سواری کے لیے محفوظ کریں", "zh": "保存此卡以供以后行程使用", "de": "Diese Karte für künftige Fahrten speichern", "it": "Salva questa carta per le prossime corse",
  "ru": "Сохранить эту карту для будущих поездок", "tr": "Bu kartı sonraki yolculuklar için kaydet", "ko": "다음 이동을 위해 이 카드 저장", "ja": "今後の乗車のためにこのカードを保存する",
  "vi": "Lưu thẻ này cho các chuyến đi sau", "fa": "این کارت را برای سفر بعدی ذخیره کنید", "th": "บันทึกบัตรนี้สำหรับการเดินทางครั้งต่อไป"
};

NOEL_I18N["status.test_mode_short"] = {
  "en": "Test mode — no real charge.", "es": "Modo de prueba: sin cargo real.", "fr": "Mode test — aucun débit réel.", "ar": "وضع الاختبار — لا يوجد خصم حقيقي.",
  "pt": "Modo de teste — sem cobrança real.", "ur": "Test mode — koi real charge nahi.", "hi": "टेस्ट मोड — कोई असली शुल्क नहीं।", "bn": "টেস্ট মোড — কোনো আসল চার্জ নেই।",
  "ud": "ٹیسٹ موڈ — کوئی حقیقی چارج نہیں", "zh": "测试模式——不收取实际费用。", "de": "Testmodus — keine echte Abbuchung.", "it": "Modalità test — nessun addebito reale.",
  "ru": "Тестовый режим — реальная оплата не списывается.", "tr": "Test modu — gerçek ücret alınmaz.", "ko": "테스트 모드 — 실제 요금이 청구되지 않습니다.", "ja": "テストモード — 実際の請求はありません。",
  "vi": "Chế độ thử nghiệm — không tính phí thật.", "fa": "حالت آزمایشی — هیچ هزینهٔ واقعی نیست", "th": "โหมดทดสอบ — ไม่มีการเรียกเก็บเงินจริง"
};

NOEL_I18N["status.test_booking_rest"] = {
  "en": "This booking was paid in test mode; no real payment was taken.", "es": "Esta reserva se pagó en modo de prueba; no se cobró nada real.", "fr": "Cette réservation a été payée en mode test ; aucun paiement réel n'a été prélevé.", "ar": "تم دفع هذا الحجز في وضع الاختبار؛ ولم يتم خصم أي مبلغ حقيقي.",
  "pt": "Esta reserva foi paga em modo de teste; nenhum pagamento real foi cobrado.", "ur": "Ye booking test mode mein pay hui; koi real payment nahi liya gaya.", "hi": "यह बुकिंग टेस्ट मोड में भुगतान की गई; कोई असली भुगतान नहीं लिया गया।", "bn": "এই বুকিং টেস্ট মোডে পে করা হয়েছে; কোনো আসল পেমেন্ট নেওয়া হয়নি।",
  "ud": "یہ بکنگ ٹیسٹ موڈ میں ادا کی گئی تھی، کوئی حقیقی ادائیگی نہیں ہوئی", "zh": "此预订已在测试模式下支付；未收取实际付款。", "de": "Diese Buchung wurde im Testmodus bezahlt; es wurde keine echte Zahlung vorgenommen.", "it": "Questa prenotazione è stata pagata in modalità test; non è stato effettuato alcun pagamento reale.",
  "ru": "Это бронирование было оплачено в тестовом режиме; реальный платёж не был списан.", "tr": "Bu rezervasyon test modunda ödendi; gerçek bir ödeme alınmadı.", "ko": "이 예약은 테스트 모드로 결제되었으며 실제 결제는 이루어지지 않았습니다.", "ja": "この予約はテストモードで支払われました。実際の支払いは行われていません。",
  "vi": "Đặt xe này đã được thanh toán trong chế độ thử nghiệm; không có khoản thanh toán thật nào được thực hiện.", "fa": "این رزرو در حالت آزمایشی پرداخت شد، هیچ پرداخت واقعی صورت نگرفت", "th": "การจองนี้ชำระในโหมดทดสอบ ไม่มีการชำระเงินจริง"
};

NOEL_I18N["status.cancel_booking"] = {
  "en": "Cancel this booking", "es": "Cancelar esta reserva", "fr": "Annuler cette réservation", "ar": "ألغِ هذا الحجز",
  "pt": "Cancelar esta reserva", "ur": "Ye booking cancel karen", "hi": "यह बुकिंग रद्द करें", "bn": "এই বুকিং বাতিল করুন",
  "ud": "یہ بکنگ منسوخ کریں", "zh": "取消此预订", "de": "Diese Buchung stornieren", "it": "Annulla questa prenotazione",
  "ru": "Отменить это бронирование", "tr": "Bu rezervasyonu iptal et", "ko": "이 예약 취소", "ja": "この予約をキャンセルする",
  "vi": "Hủy đặt xe này", "fa": "لغو این رزرو", "th": "ยกเลิกการจองนี้"
};

NOEL_I18N["status.return_trip"] = {
  "en": "Your return trip", "es": "Tu viaje de regreso", "fr": "Votre trajet retour", "ar": "رحلة عودتك",
  "pt": "Sua viagem de volta", "ur": "Aapki return trip", "hi": "आपकी वापसी यात्रा", "bn": "আপনার ফেরার যাত্রা",
  "ud": "آپ کی واپسی کی سواری", "zh": "您的返程", "de": "Ihre Rückfahrt", "it": "Il tuo viaggio di ritorno",
  "ru": "Ваша обратная поездка", "tr": "Dönüş yolculuğunuz", "ko": "귀환 여정", "ja": "帰りの乗車",
  "vi": "Chuyến về của bạn", "fa": "سفر برگشت شما", "th": "เที่ยวกลับของคุณ"
};

NOEL_I18N["status.another_ride"] = {
  "en": "Another ride", "es": "Otro viaje", "fr": "Un autre trajet", "ar": "رحلة أخرى",
  "pt": "Outra viagem", "ur": "Ek aur ride", "hi": "एक और सवारी", "bn": "আরেকটি রাইড",
  "ud": "دوسری سواری", "zh": "再来一次行程", "de": "Eine weitere Fahrt", "it": "Un'altra corsa",
  "ru": "Ещё одна поездка", "tr": "Başka bir yolculuk", "ko": "다른 이동", "ja": "別の乗車",
  "vi": "Một chuyến đi khác", "fa": "سفر دیگر", "th": "การเดินทางอื่น"
};

NOEL_I18N["status.test_booking_note"] = {
  "en": "Test mode — no real charge. This booking was paid in test mode; no real payment was taken.", "es": "Modo de prueba: sin cargo real. Esta reserva se pagó en modo de prueba; no se cobró nada real.", "fr": "Mode test — aucun débit réel. Cette réservation a été payée en mode test ; aucun paiement réel n'a été prélevé.", "ar": "وضع الاختبار — لا يوجد خصم حقيقي. تم دفع هذا الحجز في وضع الاختبار؛ ولم يتم خصم أي مبلغ حقيقي.",
  "pt": "Modo de teste — sem cobrança real. Esta reserva foi paga em modo de teste; nenhum pagamento real foi cobrado.", "ur": "Test mode — koi real charge nahi. Ye booking test mode mein pay hui; koi real payment nahi liya gaya.", "hi": "टेस्ट मोड — कोई असली शुल्क नहीं। यह बुकिंग टेस्ट मोड में भुगतान की गई; कोई असली भुगतान नहीं लिया गया।", "bn": "টেস্ট মোড — কোনো আসল চার্জ নেই। এই বুকিং টেস্ট মোডে পে করা হয়েছে; কোনো আসল পেমেন্ট নেওয়া হয়নি।",
  "ud": "ٹیسٹ موڈ — کوئی حقیقی چارج نہیں۔ یہ بکنگ ٹیسٹ موڈ میں ادا کی گئی تھی، کوئی حقیقی ادائیگی نہیں ہوئی", "zh": "测试模式——不收取实际费用。此预订已在测试模式下支付；未收取实际付款。", "de": "Testmodus — keine echte Abbuchung. Diese Buchung wurde im Testmodus bezahlt; es wurde keine echte Zahlung vorgenommen.", "it": "Modalità test — nessun addebito reale. Questa prenotazione è stata pagata in modalità test; non è stato effettuato alcun pagamento reale.",
  "ru": "Тестовый режим — реальная оплата не списывается. Это бронирование было оплачено в тестовом режиме; реальный платёж не был списан.", "tr": "Test modu — gerçek ücret alınmaz. Bu rezervasyon test modunda ödendi; gerçek bir ödeme alınmadı.", "ko": "테스트 모드 — 실제 요금이 청구되지 않습니다. 이 예약은 테스트 모드로 결제되었으며 실제 결제는 이루어지지 않았습니다.", "ja": "テストモード — 実際の請求はありません。この予約はテストモードで支払われました。実際の支払いは行われていません。",
  "vi": "Chế độ thử nghiệm — không tính phí thật. Đặt xe này đã được thanh toán trong chế độ thử nghiệm; không có khoản thanh toán thật nào được thực hiện.", "fa": "حالت آزمایشی — هیچ هزینهٔ واقعی نیست. این رزرو در حالت آزمایشی پرداخت شد، هیچ پرداخت واقعی صورت نگرفت", "th": "โหมดทดสอบ — ไม่มีการเรียกเก็บเงินจริง การจองนี้ชำระในโหมดทดสอบ ไม่มีการชำระเงินจริง"
};

NOEL_I18N["home.travel_terms"] = {
  "en": "Travel on your own terms.", "es": "Viaja a tu manera.", "fr": "Voyagez à votre façon.", "ar": "سافر بشروطك الخاصة.",
  "pt": "Viaje do seu jeito.", "ur": "Apni marzi se safar karen.", "hi": "अपनी शर्तों पर यात्रा करें।", "bn": "নিজের মতো করে ভ্রমণ করুন।",
  "ud": "اپنی شرائط پر سفر کریں", "zh": "按您的方式出行。", "de": "Reisen Sie zu Ihren eigenen Bedingungen.", "it": "Viaggia alle tue condizioni.",
  "ru": "Путешествуйте на своих условиях.", "tr": "Kendi koşullarınızla seyahat edin.", "ko": "고객님의 조건대로 이동하세요.", "ja": "お客様の条件で移動。",
  "vi": "Du lịch theo điều kiện của bạn.", "fa": "با شرایط خود سفر کنید", "th": "เดินทางตามเงื่อนไขของคุณ"
};

NOEL_I18N["home.travel_terms_p"] = {
  "en": "Premium service, absolute privacy and seamless journeys.", "es": "Servicio premium, privacidad absoluta y viajes sin complicaciones.", "fr": "Service premium, confidentialité absolue et trajets sans accroc.", "ar": "خدمة مميزة وخصوصية تامة ورحلات سلسة.",
  "pt": "Serviço premium, privacidade absoluta e viagens sem complicações.", "ur": "Premium service, poori privacy aur aaram se safar.", "hi": "प्रीमियम सेवा, पूर्ण गोपनीयता और सहज यात्रा।", "bn": "প্রিমিয়াম পরিষেবা, সম্পূর্ণ গোপনীয়তা ও মসৃণ যাত্রা।",
  "ud": "پریمیم سروس، مکمل پرائیویسی، اور ہموار سواری", "zh": "高端服务、绝对隐私和无缝旅程。", "de": "Premium-Service, absolute Privatsphäre und nahtlose Fahrten.", "it": "Servizio premium, assoluta privacy e viaggi senza intoppi.",
  "ru": "Премиальный сервис, абсолютная конфиденциальность и безупречные поездки.", "tr": "Premium hizmet, mutlak gizlilik ve sorunsuz yolculuklar.", "ko": "프리미엄 서비스, 완벽한 프라이버시, 원활한 여정.", "ja": "プレミアムサービス、完全なプライバシー、シームレスな旅。",
  "vi": "Dịch vụ cao cấp, riêng tư tuyệt đối và hành trình liền mạch.", "fa": "خدمات ممتاز، حریم خصوصی کامل و سواری نرم", "th": "บริการระดับพรีเมียม ความเป็นส่วนตัวสมบูรณ์ และการเดินทางที่ราบรื่น"
};

NOEL_I18N["home.punctual"] = {
  "en": "Punctual.", "es": "Puntual.", "fr": "Ponctuel.", "ar": "دقيق في المواعيد.",
  "pt": "Pontual.", "ur": "Waqt ka paband.", "hi": "समयनिष्ठ।", "bn": "সময়নিষ্ঠ।",
  "ud": "وقت کے پابند", "zh": "准时。", "de": "Pünktlich.", "it": "Puntuale.",
  "ru": "Пунктуально.", "tr": "Dakik.", "ko": "정시.", "ja": "時間厳守。",
  "vi": "Đúng giờ.", "fa": "وقت‌شناس", "th": "ตรงต่อเวลา"
};

NOEL_I18N["home.professional"] = {
  "en": "Professional.", "es": "Profesional.", "fr": "Professionnel.", "ar": "محترف.",
  "pt": "Profissional.", "ur": "Professional.", "hi": "पेशेवर।", "bn": "পেশাদার।",
  "ud": "پیشہ ورانہ", "zh": "专业。", "de": "Professionell.", "it": "Professionale.",
  "ru": "Профессионально.", "tr": "Profesyonel.", "ko": "전문적.", "ja": "プロフェッショナル。",
  "vi": "Chuyên nghiệp.", "fa": "حرفه‌ای", "th": "มืออาชีพ"
};

NOEL_I18N["home.punctual_p"] = {
  "en": "Our hand-selected chauffeurs prioritise your schedule, route and comfort, ensuring you arrive refreshed for what matters.", "es": "Nuestros chóferes seleccionados a mano priorizan tu horario, tu ruta y tu comodidad, para que llegues fresco a lo que importa.", "fr": "Nos chauffeurs sélectionnés avec soin privilégient votre emploi du temps, votre itinéraire et votre confort, pour que vous arriviez reposé là où cela compte.", "ar": "سائقونا المختارون بعناية يعطون الأولوية لجدولك وطريقك وراحتك، لتصل منتعشًا لما يهمك.",
  "pt": "Nossos motoristas selecionados a dedo priorizam sua agenda, sua rota e seu conforto, para que você chegue descansado ao que importa.", "ur": "Hamare haath se chune hue chauffeurs aapke time, route aur aaram ko pehle rakhte hain, taaki aap taaza hoke pahunchen jahan zaroori hai.", "hi": "हमारे हाथ से चुने हुए शॉफ़र आपके समय, मार्ग और आराम को प्राथमिकता देते हैं, ताकि आप तरोताज़ा होकर पहुँचें जहाँ ज़रूरी है।", "bn": "আমাদের হাতে বাছা শোফাররা আপনার সময়, রুট ও আরামকে অগ্রাধিকার দেন, যাতে আপনি যা গুরুত্বপূর্ণ সেখানে সতেজ হয়ে পৌঁছান।",
  "ud": "ہمارے منتخب ڈرائیور آپ کے شیڈول، راستے اور آرام کا خیال رکھتے ہیں تاکہ آپ تازہ دم پہنچیں", "zh": "我们精心挑选的司机以您的时间表、路线和舒适为先，确保您精神饱满地到达。", "de": "Unsere handverlesenen Chauffeure richten sich nach Ihrem Zeitplan, Ihrer Route und Ihrem Komfort, damit Sie erfrischt ankommen.", "it": "I nostri chauffeur selezionati danno priorità ai tuoi orari, al percorso e al comfort, per farti arrivare riposato.",
  "ru": "Наши тщательно отобранные шофёры ставят на первое место ваше расписание, маршрут и комфорт, чтобы вы прибыли отдохнувшими.", "tr": "Özenle seçilmiş şoförlerimiz programınıza, rotanıza ve konforunuza öncelik verir, böylece dinlenmiş olarak varırsınız.", "ko": "엄선된 쇼퍼가 고객님의 일정, 경로, 편안함을 최우선으로 하여 상쾌하게 도착하실 수 있도록 합니다.", "ja": "厳選されたショファーがお客様のスケジュール、ルート、快適さを最優先し、リフレッシュして到着できるようにします。",
  "vi": "Tài xế được tuyển chọn kỹ lưỡng của chúng tôi ưu tiên lịch trình, lộ trình và sự thoải mái của bạn, đảm bảo bạn đến nơi sảng khoái.", "fa": "راننده‌های منتخب ما به برنامه، مسیر و راحتی شما اهمیت می‌دهند تا سرحال برسید", "th": "คนขับที่คัดสรรมาอย่างดีของเราให้ความสำคัญกับตาราง เส้นทาง และความสะดวกสบายของคุณ เพื่อให้คุณมาถึงอย่างสดชื่น"
};

NOEL_I18N["home.learn_more"] = {
  "en": "Learn more", "es": "Más información", "fr": "En savoir plus", "ar": "اعرف المزيد",
  "pt": "Saiba mais", "ur": "Aur janen", "hi": "और जानें", "bn": "আরও জানুন",
  "ud": "مزید جانیں", "zh": "了解更多", "de": "Mehr erfahren", "it": "Scopri di più",
  "ru": "Узнать больше", "tr": "Daha fazla bilgi", "ko": "자세히 알아보기", "ja": "詳しく見る",
  "vi": "Tìm hiểu thêm", "fa": "بیشتر بدانید", "th": "เรียนรู้เพิ่มเติม"
};

NOEL_I18N["home.why"] = {
  "en": "Why ride with Noel Chauffer", "es": "Por qué viajar con Noel Chauffer", "fr": "Pourquoi voyager avec Noel Chauffer", "ar": "لماذا تسافر مع نويل شوفير",
  "pt": "Por que viajar com a Noel Chauffer", "ur": "Noel Chauffer ke saath safar kyun karen", "hi": "नोएल शॉफ़र के साथ यात्रा क्यों करें", "bn": "নোয়েল শোফারের সঙ্গে কেন ভ্রমণ করবেন",
  "ud": "Noel Chauffer کے ساتھ کیوں سفر کریں", "zh": "为什么选择 Noel Chauffer", "de": "Warum mit Noel Chauffer fahren", "it": "Perché viaggiare con Noel Chauffer",
  "ru": "Почему стоит ездить с Noel Chauffer", "tr": "Neden Noel Chauffer ile yolculuk yapmalısınız", "ko": "Noel Chauffer를 이용해야 하는 이유", "ja": "Noel Chaufferで乗車する理由",
  "vi": "Tại sao nên đi cùng Noel Chauffer", "fa": "چرا با Noel Chauffer سفر کنید", "th": "ทำไมต้องเดินทางกับ Noel Chauffer"
};

NOEL_I18N["home.why_intro"] = {
  "en": "A calm ride starts long before pickup.", "es": "Un viaje tranquilo empieza mucho antes de la recogida.", "fr": "Un trajet calme commence bien avant la prise en charge.", "ar": "الرحلة الهادئة تبدأ قبل الاستلام بوقت طويل.",
  "pt": "Uma viagem tranquila começa muito antes do embarque.", "ur": "Aaram wali ride pickup se bahut pehle shuru hoti hai.", "hi": "आरामदायक सवारी पिकअप से बहुत पहले शुरू होती है।", "bn": "শান্ত রাইড পিকআপের অনেক আগেই শুরু হয়।",
  "ud": "پرسکون سواری پک اپ سے بہت پہلے شروع ہوتی ہے", "zh": "一次安静的行程在接送之前很久就开始了。", "de": "Eine ruhige Fahrt beginnt lange vor der Abholung.", "it": "Una corsa tranquilla inizia molto prima del ritiro.",
  "ru": "Спокойная поездка начинается задолго до подачи.", "tr": "Sakin bir yolculuk, binişten çok önce başlar.", "ko": "차분한 이동은 픽업 훨씬 전부터 시작됩니다.", "ja": "落ち着いた乗車は、乗車のはるか前から始まります。",
  "vi": "Một chuyến đi yên tĩnh bắt đầu từ rất lâu trước khi đón.", "fa": "سواری آرام خیلی پیش از زمان سوارشدن آغاز می‌شود", "th": "การเดินทางที่สงบเริ่มต้นนานก่อนเวลารับ"
};

NOEL_I18N["home.pro_chauffeurs"] = {
  "en": "Professional chauffeurs", "es": "Chóferes profesionales", "fr": "Chauffeurs professionnels", "ar": "سائقون محترفون",
  "pt": "Motoristas profissionais", "ur": "Professional chauffeurs", "hi": "पेशेवर शॉफ़र", "bn": "পেশাদার শোফার",
  "ud": "پیشہ ور ڈرائیور", "zh": "专业司机", "de": "Professionelle Chauffeure", "it": "Chauffeur professionisti",
  "ru": "Профессиональные шофёры", "tr": "Profesyonel şoförler", "ko": "전문 쇼퍼", "ja": "プロのショファー",
  "vi": "Tài xế chuyên nghiệp", "fa": "راننده‌های حرفه‌ای", "th": "คนขับมืออาชีพ"
};

NOEL_I18N["home.pro_chauffeurs_p"] = {
  "en": "Polite, experienced drivers who know the roads and respect your time.", "es": "Conductores educados y con experiencia que conocen las carreteras y respetan tu tiempo.", "fr": "Des chauffeurs polis et expérimentés qui connaissent les routes et respectent votre temps.", "ar": "سائقون مهذبون وذوو خبرة يعرفون الطرق ويحترمون وقتك.",
  "pt": "Motoristas educados e experientes que conhecem as estradas e respeitam seu tempo.", "ur": "Shareef aur tajurbekaar drivers jo raaste jaante hain aur aapke time ki qadar karte hain.", "hi": "विनम्र, अनुभवी ड्राइवर जो सड़कें जानते हैं और आपके समय का सम्मान करते हैं।", "bn": "ভদ্র, অভিজ্ঞ চালক যারা রাস্তা জানেন এবং আপনার সময়কে সম্মান করেন।",
  "ud": "شائستہ، تجربہ کار ڈرائیور جو سڑکیں جانتا ہے اور آپ کے وقت کی قدر کرتا ہے", "zh": "礼貌、经验丰富的司机，熟悉路况并尊重您的时间。", "de": "Höfliche, erfahrene Fahrer, die die Straßen kennen und Ihre Zeit respektieren.", "it": "Autisti educati ed esperti, che conoscono le strade e rispettano il tuo tempo.",
  "ru": "Вежливые, опытные водители, которые знают дороги и уважают ваше время.", "tr": "Yolları bilen ve zamanınıza saygı duyan kibar, deneyimli sürücüler.", "ko": "도로를 잘 알고 고객님의 시간을 존중하는 정중하고 경험 많은 기사.", "ja": "道路を熟知し、お客様の時間を尊重する礼儀正しく経験豊富なドライバー。",
  "vi": "Tài xế lịch sự, giàu kinh nghiệm, am hiểu đường sá và tôn trọng thời gian của bạn.", "fa": "رانندهٔ مؤدب و باتجربه که جاده‌ها را می‌شناسد و به وقت شما احترام می‌گذارد", "th": "คนขับสุภาพ มีประสบการณ์ รู้จักถนนและเคารพเวลาของคุณ"
};

NOEL_I18N["home.recent_cars"] = {
  "en": "Recent high-end cars", "es": "Coches recientes de alta gama", "fr": "Voitures récentes haut de gamme", "ar": "سيارات حديثة فاخرة",
  "pt": "Carros recentes de alto padrão", "ur": "Nayi high-end gaadiyan", "hi": "नई उच्च-स्तरीय गाड़ियाँ", "bn": "নতুন উঁচুমানের গাড়ি",
  "ud": "نئی لگژری گاڑیاں", "zh": "较新的高端车辆", "de": "Neueste hochwertige Autos", "it": "Auto recenti di fascia alta",
  "ru": "Новые автомобили высокого класса", "tr": "Yeni üst sınıf araçlar", "ko": "최신 고급 차량", "ja": "最新のハイエンド車",
  "vi": "Xe cao cấp đời mới", "fa": "خودروهای لوکس جدید", "th": "รถยนต์ระดับสูงรุ่นใหม่"
};

NOEL_I18N["home.recent_cars_p"] = {
  "en": "Clean, comfortable, recent cars, ready for every ride.", "es": "Coches limpios, cómodos y recientes, listos para cada viaje.", "fr": "Des voitures propres, confortables et récentes, prêtes pour chaque trajet.", "ar": "سيارات نظيفة ومريحة وحديثة، جاهزة لكل رحلة.",
  "pt": "Carros limpos, confortáveis e recentes, prontos para cada viagem.", "ur": "Saaf, aaramdeh, nayi gaadiyan — har ride ke liye ready.", "hi": "साफ़, आरामदायक, नई गाड़ियाँ — हर सवारी के लिए तैयार।", "bn": "পরিষ্কার, আরামদায়ক, নতুন গাড়ি — প্রতিটি রাইডের জন্য প্রস্তুত।",
  "ud": "صاف ستھری، آرام دہ، نئی گاڑیاں، ہر سواری کے لیے تیار", "zh": "干净、舒适、较新的车辆，随时为每次行程做好准备。", "de": "Saubere, komfortable, neuere Autos, bereit für jede Fahrt.", "it": "Auto pulite, confortevoli e recenti, pronte per ogni corsa.",
  "ru": "Чистые, комфортабельные, новые автомобили, готовые к любой поездке.", "tr": "Temiz, konforlu, yeni araçlar, her yolculuğa hazır.", "ko": "깨끗하고 편안한 최신 차량으로 모든 이동에 대비되어 있습니다.", "ja": "清潔で快適な最新車両、あらゆる乗車に対応可能。",
  "vi": "Xe sạch sẽ, thoải mái, đời mới, sẵn sàng cho mọi chuyến đi.", "fa": "خودروهای تمیز، راحت و جدید، آماده برای هر سفر", "th": "รถยนต์สะอาด สะดวกสบาย รุ่นใหม่ พร้อมสำหรับการเดินทางทุกครั้ง"
};

NOEL_I18N["home.ontime"] = {
  "en": "On-time pickups", "es": "Recogidas puntuales", "fr": "Prises en charge à l'heure", "ar": "استلام في الوقت المحدد",
  "pt": "Embarques pontuais", "ur": "Waqt par pickups", "hi": "समय पर पिकअप", "bn": "সময়মতো পিকআপ",
  "ud": "وقت پر", "zh": "准时接送", "de": "Pünktliche Abholungen", "it": "Ritiri puntuali",
  "ru": "Пунктуальная подача", "tr": "Zamanında biniş", "ko": "정시 픽업", "ja": "時間通りの乗車",
  "vi": "Đón đúng giờ", "fa": "سر وقت", "th": "รับตรงเวลา"
};

NOEL_I18N["home.ontime_p"] = {
  "en": "Your chauffeur plans the route and arrives on time, every time.", "es": "Tu chófer planifica la ruta y llega a tiempo, siempre.", "fr": "Votre chauffeur planifie l'itinéraire et arrive à l'heure, à chaque fois.", "ar": "سائقك يخطط للطريق ويصل في الوقت المحدد، في كل مرة.",
  "pt": "Seu motorista planeja a rota e chega na hora, sempre.", "ur": "Aapka chauffeur route plan karta hai aur har baar waqt par aata hai.", "hi": "आपका शॉफ़र रास्ता तय करता है और हर बार समय पर पहुँचता है।", "bn": "আপনার শোফার রুট পরিকল্পনা করেন এবং প্রতিবার সময়মতো পৌঁছান।",
  "ud": "آپ کا ڈرائیور راستہ منصوبہ بندی کرتا ہے اور ہر بار وقت پر پہنچتا ہے", "zh": "您的司机会规划路线，每次都准时到达。", "de": "Ihr Chauffeur plant die Route und kommt jedes Mal pünktlich an.", "it": "Il tuo chauffeur pianifica il percorso e arriva in orario, ogni volta.",
  "ru": "Ваш шофёр планирует маршрут и всегда приезжает вовремя.", "tr": "Şoförünüz rotayı planlar ve her seferinde zamanında varır.", "ko": "쇼퍼가 경로를 계획하고 매번 정시에 도착합니다.", "ja": "ショファーがルートを計画し、毎回時間通りに到着します。",
  "vi": "Tài xế của bạn lên kế hoạch lộ trình và đến đúng giờ, mọi lúc.", "fa": "رانندهٔ شما مسیر را برنامه‌ریزی می‌کند و هر بار سر وقت می‌رسد", "th": "คนขับของคุณวางแผนเส้นทางและมาถึงตรงเวลาทุกครั้ง"
};

NOEL_I18N["home.three_ways"] = {
  "en": "Three ways to ride", "es": "Tres formas de viajar", "fr": "Trois façons de voyager", "ar": "ثلاث طرق للسفر",
  "pt": "Três maneiras de viajar", "ur": "Safar ke teen tareeqe", "hi": "यात्रा के तीन तरीके", "bn": "ভ্রমণের তিনটি উপায়",
  "ud": "سفر کے تین طریقے", "zh": "三种出行方式", "de": "Drei Arten zu fahren", "it": "Tre modi di viaggiare",
  "ru": "Три способа ездить", "tr": "Yolculuk yapmanın üç yolu", "ko": "세 가지 이동 방법", "ja": "3つの乗車方法",
  "vi": "Ba cách để đi", "fa": "سه راه برای سفر", "th": "สามวิธีในการเดินทาง"
};

NOEL_I18N["home.three_ways_intro"] = {
  "en": "Every booking works the same way: choose your class and pay by card — then your chauffeur is assigned.", "es": "Cada reserva funciona igual: elige tu clase y paga con tarjeta; luego se asigna tu chófer.", "fr": "Chaque réservation fonctionne de la même façon : choisissez votre classe et payez par carte — votre chauffeur sera ensuite assigné.", "ar": "كل حجز يعمل بالطريقة نفسها: اختر فئتك وادفع بالبطاقة — ثم يتم تعيين سائقك.",
  "pt": "Cada reserva funciona da mesma forma: escolha sua classe e pague com cartão — depois seu motorista é designado.", "ur": "Har booking ek hi tarah kaam karti hai: apni class chunen aur card se pay karen — phir aapka chauffeur assign ho jayega.", "hi": "हर बुकिंग एक ही तरह से काम करती है: अपनी श्रेणी चुनें और कार्ड से भुगतान करें — फिर आपका शॉफ़र नियुक्त हो जाएगा।", "bn": "প্রতিটি বুকিং একইভাবে কাজ করে: আপনার শ্রেণি বেছে নিন ও কার্ডে পেমেন্ট করুন — তারপর আপনার শোফার নিয়োগ করা হবে।",
  "ud": "ہر بکنگ اسی طرح کام کرتی ہے: اپنی کلاس منتخب کریں اور کارڈ سے ادائیگی کریں — پھر آپ کا ڈرائیور مقرر ہو جاتا ہے", "zh": "每次预订都一样：选择级别并用卡支付——然后为您指派司机。", "de": "Jede Buchung funktioniert gleich: Wählen Sie Ihre Klasse und bezahlen Sie per Karte — dann wird Ihr Chauffeur zugewiesen.", "it": "Ogni prenotazione funziona allo stesso modo: scegli la tua classe e paga con carta — poi ti viene assegnato il tuo chauffeur.",
  "ru": "Каждое бронирование работает одинаково: выберите класс и оплатите картой — затем вам назначается ваш шофёр.", "tr": "Her rezervasyon aynı şekilde çalışır: sınıfınızı seçin ve kartla ödeyin — ardından şoförünüz atanır.", "ko": "모든 예약은 같은 방식으로 진행됩니다. 클래스를 선택하고 카드로 결제하면 쇼퍼가 배정됩니다.", "ja": "すべての予約は同じ仕組みです。クラスを選択してカードでお支払いください。その後ショファーが割り当てられます。",
  "vi": "Mọi đặt xe đều hoạt động giống nhau: chọn hạng của bạn và thanh toán bằng thẻ — sau đó tài xế của bạn sẽ được chỉ định.", "fa": "هر رزرو به یک شکل کار می‌کند: کلاس خود را انتخاب کنید و با کارت پرداخت کنید — سپس رانندهٔ شما تعیین می‌شود", "th": "การจองทุกครั้งทำงานเหมือนกัน: เลือกระดับของคุณและชำระเงินด้วยบัตร — จากนั้นคนขับของคุณจะได้รับมอบหมาย"
};

NOEL_I18N["home.airport_transfers"] = {
  "en": "Airport Transfers", "es": "Traslados al aeropuerto", "fr": "Transferts aéroport", "ar": "النقل من وإلى المطار",
  "pt": "Transfers de aeroporto", "ur": "Airport Transfers", "hi": "एयरपोर्ट ट्रांसफर", "bn": "বিমানবন্দর ট্রান্সফার",
  "ud": "ہوائی اڈے کی منتقلی", "zh": "机场接送", "de": "Flughafentransfers", "it": "Trasferimenti aeroportuali",
  "ru": "Трансферы в аэропорт", "tr": "Havalimanı Transferleri", "ko": "공항 이동", "ja": "空港送迎",
  "vi": "Đưa đón sân bay", "fa": "ترانسفر فرودگاه", "th": "รับส่งสนามบิน"
};

NOEL_I18N["home.airport_p"] = {
  "en": "Flying in or out of JFK, LaGuardia, Newark, LAX, ORD or MIA? Your chauffeur meets you at the right terminal. Add your flight number when you book, and take your time — airport pickups include 60 minutes of free waiting.", "es": "¿Vuelas desde o hacia JFK, LaGuardia, Newark, LAX, ORD o MIA? Tu chófer te espera en la terminal correcta. Añade tu número de vuelo al reservar y tómate tu tiempo: las recogidas en el aeropuerto incluyen 60 minutos de espera gratis.", "fr": "Vous partez ou arrivez à JFK, LaGuardia, Newark, LAX, ORD ou MIA ? Votre chauffeur vous attend au bon terminal. Ajoutez votre numéro de vol lors de la réservation et prenez votre temps — les prises en charge à l'aéroport incluent 60 minutes d'attente gratuite.", "ar": "هل تسافر من أو إلى مطارات JFK أو LaGuardia أو Newark أو LAX أو ORD أو MIA؟ سيلقاك سائقك في الصالة الصحيحة. أضف رقم رحلتك عند الحجز وخذ وقتك — يشمل الاستلام من المطار 60 دقيقة انتظار مجاني.",
  "pt": "Voando de ou para JFK, LaGuardia, Newark, LAX, ORD ou MIA? Seu motorista encontrará você no terminal certo. Adicione o número do seu voo ao reservar e não tenha pressa — embarques no aeroporto incluem 60 minutos de espera gratuita.", "ur": "JFK, LaGuardia, Newark, LAX, ORD ya MIA se aa rahe hain ya ja rahe hain? Aapka chauffeur sahi terminal par milega. Book karte waqt apni flight number likhen aur aaram se aayen — airport pickups mein 60 minutes free waiting hai.", "hi": "JFK, LaGuardia, Newark, LAX, ORD या MIA से आ रहे हैं या जा रहे हैं? आपका शॉफ़र सही टर्मिनल पर मिलेगा। बुक करते समय अपनी फ़्लाइट संख्या जोड़ें और आराम से आएँ — एयरपोर्ट पिकअप में 60 मिनट की मुफ़्त प्रतीक्षा शामिल है।", "bn": "JFK, LaGuardia, Newark, LAX, ORD বা MIA থেকে আসছেন বা যাচ্ছেন? আপনার শোফার সঠিক টার্মিনালে দেখা করবেন। বুক করার সময় আপনার ফ্লাইট নম্বর যোগ করুন এবং সময় নিন — বিমানবন্দর পিকআপে ৬০ মিনিট বিনামূল্যে অপেক্ষা অন্তর্ভুক্ত।",
  "ud": "JFK، LaGuardia، Newark، LAX، ORD یا MIA سے پرواز پر جا رہے ہیں یا آ رہے ہیں؟ آپ کا ڈرائیور آپ سے صحیح ٹرمینل پر ملے گا، بکنگ کے وقت اپنا فلائٹ نمبر شامل کریں، اور اپنا وقت لیں — ہوائی اڈے کی پک اپ میں 60 منٹ کا مفت انتظار شامل ہے", "zh": "从 JFK、拉瓜迪亚、纽瓦克、LAX、ORD 或 MIA 出发或到达？您的司机将在正确的航站楼迎接您。预订时请添加航班号，不用着急——机场接送包含60分钟免费等候。", "de": "Fliegen Sie von JFK, LaGuardia, Newark, LAX, ORD oder MIA ab oder kommen Sie dort an? Ihr Chauffeur erwartet Sie am richtigen Terminal. Geben Sie bei der Buchung Ihre Flugnummer an und lassen Sie sich Zeit — Abholungen am Flughafen beinhalten 60 Minuten kostenlose Wartezeit.", "it": "In partenza o in arrivo da JFK, LaGuardia, Newark, LAX, ORD o MIA? Il tuo chauffeur ti aspetta al terminal giusto. Aggiungi il numero di volo quando prenoti e prenditi il tuo tempo — i ritiri in aeroporto includono 60 minuti di attesa gratuita.",
  "ru": "Вылетаете из JFK, Ла-Гуардия, Ньюарк, LAX, ORD или MIA или прилетаете туда? Ваш шофёр встретит вас у нужного терминала. Добавьте номер рейса при бронировании и не торопитесь — подача в аэропорту включает 60 минут бесплатного ожидания.", "tr": "JFK, LaGuardia, Newark, LAX, ORD veya MIA'ya mı uçuyorsunuz? Şoförünüz sizi doğru terminalde karşılar. Rezervasyon yaparken uçuş numaranızı ekleyin ve zaman ayırın — havalimanı binişleri 60 dakika ücretsiz bekleme içerir.", "ko": "JFK, 라과디아, 뉴어크, LAX, ORD, MIA에서 출발하거나 도착하시나요? 쇼퍼가 올바른 터미널에서 맞이합니다. 예약 시 항공편 번호를 추가하고 여유를 가지세요. 공항 픽업에는 60분 무료 대기가 포함됩니다.", "ja": "JFK、ラガーディア、ニューアーク、LAX、ORD、MIAへの出発または到着ですか？ショファーが正しいターミナルでお迎えします。予約時に便名を追加し、ゆっくりしてください。空港での乗車には60分の無料待ち時間が含まれます。",
  "vi": "Bay đến hoặc đi từ JFK, LaGuardia, Newark, LAX, ORD hay MIA? Tài xế của bạn sẽ gặp bạn tại nhà ga đúng. Thêm số hiệu chuyến bay khi bạn đặt xe và cứ thong thả — đón tại sân bay bao gồm 60 phút chờ miễn phí.", "fa": "از JFK، LaGuardia، Newark، LAX، ORD یا MIA پرواز دارید یا به آن می‌رسید؟ رانندهٔ شما در ترمینال صحیح با شما ملاقات می‌کند، هنگام رزرو شمارهٔ پرواز خود را اضافه کنید و با آرامش وقت بگذرانید — سوارشدن در فرودگاه شامل ۶۰ دقیقه انتظار رایگان است", "th": "บินเข้าหรือออกจาก JFK, LaGuardia, Newark, LAX, ORD หรือ MIA? คนขับของคุณจะพบคุณที่อาคารผู้โดยสารที่ถูกต้อง เพิ่มหมายเลขเที่ยวบินเมื่อจอง และใช้เวลาของคุณ — การรับที่สนามบินรวมเวลารอฟรี 60 นาที"
};

NOEL_I18N["home.airport_learn"] = {
  "en": "Learn more about airport transfers", "es": "Más información sobre traslados al aeropuerto", "fr": "En savoir plus sur les transferts aéroport", "ar": "اعرف المزيد عن النقل من وإلى المطار",
  "pt": "Saiba mais sobre transfers de aeroporto", "ur": "Airport transfers ke baare mein aur janen", "hi": "एयरपोर्ट ट्रांसफर के बारे में और जानें", "bn": "বিমানবন্দর ট্রান্সফার সম্পর্কে আরও জানুন",
  "ud": "ہوائی اڈے کی منتقلی کے بارے میں مزید جانیں", "zh": "了解更多机场接送信息", "de": "Mehr über Flughafentransfers erfahren", "it": "Scopri di più sui trasferimenti aeroportuali",
  "ru": "Узнать больше о трансферах в аэропорт", "tr": "Havalimanı transferleri hakkında daha fazla bilgi", "ko": "공항 이동에 대해 자세히 알아보기", "ja": "空港送迎について詳しく見る",
  "vi": "Tìm hiểu thêm về đưa đón sân bay", "fa": "دربارهٔ ترانسفر فرودگاه بیشتر بدانید", "th": "เรียนรู้เพิ่มเติมเกี่ยวกับการรับส่งสนามบิน"
};

NOEL_I18N["home.point_to_point"] = {
  "en": "Point to Point", "es": "De puerta a puerta", "fr": "Point à point", "ar": "من نقطة إلى نقطة",
  "pt": "Ponto a ponto", "ur": "Point to Point", "hi": "पॉइंट टू पॉइंट", "bn": "পয়েন্ট টু পয়েন্ট",
  "ud": "پوائنٹ سے پوائنٹ", "zh": "点对点", "de": "Von Punkt zu Punkt", "it": "Da punto a punto",
  "ru": "Из точки в точку", "tr": "Noktadan Noktaya", "ko": "지점 간 이동", "ja": "ポイントツーポイント",
  "vi": "Từ điểm này đến điểm khác", "fa": "نقطه‌به‌نقطه", "th": "จากจุดหนึ่งไปยังอีกจุดหนึ่ง"
};

NOEL_I18N["home.point_p"] = {
  "en": "One ride from one address to another, anywhere in the USA. Home to the office, hotel to dinner, or across state lines — your chauffeur takes you straight there, on time.", "es": "Un viaje de una dirección a otra, en cualquier lugar de EE. UU. De casa a la oficina, del hotel a la cena o a través de estados: tu chófer te lleva directo, a tiempo.", "fr": "Un trajet d'une adresse à une autre, partout aux États-Unis. De la maison au bureau, de l'hôtel au dîner, ou d'un État à l'autre — votre chauffeur vous y conduit directement, à l'heure.", "ar": "رحلة واحدة من عنوان إلى آخر، في أي مكان في الولايات المتحدة. من المنزل إلى المكتب، أو من الفندق إلى العشاء، أو عبر حدود الولايات — سائقك يوصلك مباشرة وفي الوقت المحدد.",
  "pt": "Uma viagem de um endereço a outro, em qualquer lugar dos EUA. De casa ao escritório, do hotel ao jantar ou através de estados — seu motorista leva você direto, na hora.", "ur": "Ek address se doosre address tak, USA mein kahin bhi. Ghar se office, hotel se dinner, ya state lines ke paar — aapka chauffeur aapko seedha waqt par le jayega.", "hi": "एक पते से दूसरे पते तक, अमेरिका में कहीं भी। घर से दफ़्तर, होटल से डिनर, या राज्य की सीमा पार — आपका शॉफ़र आपको सीधे समय पर ले जाएगा।", "bn": "এক ঠিকানা থেকে অন্য ঠিকানায়, যুক্তরাষ্ট্রের যেকোনো জায়গায়। বাড়ি থেকে অফিস, হোটেল থেকে ডিনার, বা রাজ্যের সীমানা পেরিয়ে — আপনার শোফার আপনাকে সোজা সময়মতো নিয়ে যাবেন।",
  "ud": "ایک پتے سے دوسرے پتے تک ایک سواری، پورے امریکہ میں۔ گھر سے دفتر، ہوٹل سے ڈنر، یا ریاستوں کے درمیان — آپ کا ڈرائیور آپ کو وقت پر وہاں پہنچاتا ہے", "zh": "从一个地址到另一个地址的一次行程，遍及美国各地。从家到办公室、从酒店到餐厅，或跨越州界——您的司机将准时直接送您到达。", "de": "Eine Fahrt von einer Adresse zur anderen, überall in den USA. Von zu Hause ins Büro, vom Hotel zum Abendessen oder über Bundesstaatsgrenzen hinweg — Ihr Chauffeur bringt Sie pünktlich direkt dorthin.", "it": "Una corsa da un indirizzo all'altro, ovunque negli USA. Da casa all'ufficio, dall'hotel alla cena o attraverso i confini di stato — il tuo chauffeur ti porta dritto lì, in orario.",
  "ru": "Одна поездка от одного адреса до другого, в любом месте США. Из дома в офис, из отеля на ужин или через границы штатов — ваш шофёр довезёт вас прямо туда, вовремя.", "tr": "Bir adresten diğerine tek yolculuk, ABD'nin her yerinde. Evden ofise, otelden akşam yemeğine veya eyalet sınırları ötesine — şoförünüz sizi zamanında doğrudan götürür.", "ko": "미국 어디서나 한 주소에서 다른 주소로 한 번의 이동. 집에서 사무실로, 호텔에서 저녁 식사 장소로, 주 경계를 넘어서까지 쇼퍼가 정시에 바로 모셔다 드립니다.", "ja": "全米どこでも、ある住所から別の住所への1回の乗車。自宅からオフィスへ、ホテルからディナーへ、州境を越えても、ショファーが時間通りに直接お連れします。",
  "vi": "Một chuyến đi từ địa chỉ này đến địa chỉ khác, ở bất cứ đâu tại Hoa Kỳ. Từ nhà đến văn phòng, từ khách sạn đến bữa tối, hoặc qua các bang — tài xế sẽ đưa bạn thẳng đến nơi, đúng giờ.", "fa": "یک سفر از یک نشانی به نشانی دیگر، در سراسر ایالات متحده. از خانه تا محل کار، از هتل تا شام، یا بین ایالت‌ها — رانندهٔ شما شما را سر وقت به آنجا می‌رساند", "th": "การเดินทางหนึ่งครั้งจากที่อยู่หนึ่งไปยังอีกที่อยู่หนึ่ง ทั่วสหรัฐอเมริกา จากบ้านไปที่ทำงาน จากโรงแรมไปทานอาหารค่ำ หรือข้ามรัฐ — คนขับของคุณพาคุณไปตรงนั้นตรงเวลา"
};

NOEL_I18N["home.point_learn"] = {
  "en": "Learn more about point-to-point rides", "es": "Más información sobre viajes de puerta a puerta", "fr": "En savoir plus sur les trajets point à point", "ar": "اعرف المزيد عن الرحلات من نقطة إلى نقطة",
  "pt": "Saiba mais sobre viagens ponto a ponto", "ur": "Point-to-point rides ke baare mein aur janen", "hi": "पॉइंट टू पॉइंट सवारी के बारे में और जानें", "bn": "পয়েন্ট টু পয়েন্ট রাইড সম্পর্কে আরও জানুন",
  "ud": "پوائنٹ سے پوائنٹ سواریوں کے بارے میں مزید جانیں", "zh": "了解更多点对点行程", "de": "Mehr über Fahrten von Punkt zu Punkt erfahren", "it": "Scopri di più sulle corse da punto a punto",
  "ru": "Узнать больше о поездках из точки в точку", "tr": "Noktadan noktaya yolculuklar hakkında daha fazla bilgi", "ko": "지점 간 이동에 대해 자세히 알아보기", "ja": "ポイントツーポイント乗車について詳しく見る",
  "vi": "Tìm hiểu thêm về chuyến đi từ điểm này đến điểm khác", "fa": "دربارهٔ سفرهای نقطه‌به‌نقطه بیشتر بدانید", "th": "เรียนรู้เพิ่มเติมเกี่ยวกับการเดินทางจากจุดหนึ่งไปยังอีกจุดหนึ่ง"
};

NOEL_I18N["home.hourly"] = {
  "en": "Hourly as Directed", "es": "Por horas, a tu disposición", "fr": "À l'heure, à votre disposition", "ar": "بالساعة حسب توجيهك",
  "pt": "Por hora, à sua disposição", "ur": "Hourly as Directed", "hi": "निर्देशानुसार घंटे के हिसाब से", "bn": "নির্দেশমতো ঘণ্টা হিসেবে",
  "ud": "جب چاہیں فی گھنٹہ", "zh": "按需按小时", "de": "Stundenweise nach Wunsch", "it": "A ore, come vuoi",
  "ru": "Почасовая аренда", "tr": "İstediğiniz Gibi Saatlik", "ko": "원하는 대로 시간제", "ja": "ご希望通りの時間貸し",
  "vi": "Theo giờ theo ý bạn", "fa": "ساعتی، هر وقت که بخواهید", "th": "รายชั่วโมงตามต้องการ"
};

NOEL_I18N["home.hourly_p"] = {
  "en": "Keep your chauffeur for as long as you need. Several stops, meetings across town, or a whole evening out — book by the hour.", "es": "Quédate con tu chófer todo el tiempo que necesites. Varias paradas, reuniones por la ciudad o toda una noche fuera: reserva por horas.", "fr": "Gardez votre chauffeur aussi longtemps que nécessaire. Plusieurs arrêts, des réunions en ville ou une soirée entière — réservez à l'heure.", "ar": "احتفظ بسائقك طالما احتجت. عدة توقفات أو اجتماعات عبر المدينة أو أمسية كاملة — احجز بالساعة.",
  "pt": "Fique com seu motorista pelo tempo que precisar. Várias paradas, reuniões pela cidade ou uma noite inteira — reserve por hora.", "ur": "Apne chauffeur ko jitni der chahiye utni der rakhen. Kai stops, sheher bhar mein meetings, ya poori shaam — hour ke hisaab se book karen.", "hi": "अपने शॉफ़र को जितनी देर चाहें उतनी देर रखें। कई रुकावटें, शहर भर में बैठकें, या पूरी शाम — घंटे के हिसाब से बुक करें।", "bn": "যতক্ষণ দরকার আপনার শোফারকে রাখুন। একাধিক স্টপ, শহরজুড়ে মিটিং, বা পুরো সন্ধ্যা — ঘণ্টা হিসেবে বুক করুন।",
  "ud": "اپنے ڈرائیور کو جتنی دیر چاہیں اپنے ساتھ رکھیں — کئی اسٹاپ، شہر بھر میں میٹنگیں، یا رات بھر کی سیر — فی گھنٹہ بک کریں", "zh": "需要多久就让司机陪伴多久。多次停靠、跨城会议或整晚外出——按小时预订。", "de": "Behalten Sie Ihren Chauffeur so lange, wie Sie ihn brauchen. Mehrere Stopps, Termine in der Stadt oder ein ganzer Abend — buchen Sie stundenweise.", "it": "Tieni il tuo chauffeur per tutto il tempo che ti serve. Più fermate, incontri in città o un'intera serata fuori — prenota a ore.",
  "ru": "Держите вашего шофёра столько, сколько вам нужно. Несколько остановок, встречи по городу или целый вечер — бронируйте почасово.", "tr": "Şoförünüzü ihtiyacınız olduğu sürece tutun. Birkaç durak, şehirde toplantılar veya bir akşam gezmesi — saatlik rezervasyon yapın.", "ko": "필요한 만큼 쇼퍼와 함께하세요. 여러 번의 정차, 시내 회의, 저녁 외출까지 시간 단위로 예약하세요.", "ja": "必要な時間だけショファーをご利用ください。複数の停留所、市内の会議、夜の外出も、時間単位で予約できます。",
  "vi": "Giữ tài xế của bạn bao lâu tùy thích. Nhiều điểm dừng, họp khắp thành phố, hoặc cả buổi tối đi chơi — đặt theo giờ.", "fa": "رانندهٔ خود را هرقدر که بخواهید نزد خود نگه دارید — چند توقف، جلسه‌ها در سراسر شهر یا یک شب بیرون — ساعتی رزرو کنید", "th": "ให้คนขับอยู่กับคุณนานเท่าที่ต้องการ หลายจุดจอด ประชุมทั่วเมือง หรือออกไปเที่ยวทั้งคืน — จองรายชั่วโมง"
};

NOEL_I18N["home.hourly_learn"] = {
  "en": "Learn more about hourly hire", "es": "Más información sobre alquiler por horas", "fr": "En savoir plus sur la location à l'heure", "ar": "اعرف المزيد عن الحجز بالساعة",
  "pt": "Saiba mais sobre aluguel por hora", "ur": "Hourly hire ke baare mein aur janen", "hi": "घंटे के हिसाब से किराए के बारे में और जानें", "bn": "ঘণ্টা হিসেবে ভাড়া সম্পর্কে আরও জানুন",
  "ud": "فی گھنٹہ کرایے کے بارے میں مزید جانیں", "zh": "了解更多按小时租用信息", "de": "Mehr über stundenweise Miete erfahren", "it": "Scopri di più sul noleggio a ore",
  "ru": "Узнать больше о почасовой аренде", "tr": "Saatlik kiralama hakkında daha fazla bilgi", "ko": "시간제 대여에 대해 자세히 알아보기", "ja": "時間貸しについて詳しく見る",
  "vi": "Tìm hiểu thêm về thuê theo giờ", "fa": "دربارهٔ کرایهٔ ساعتی بیشتر بدانید", "th": "เรียนรู้เพิ่มเติมเกี่ยวกับการเช่ารายชั่วโมง"
};

NOEL_I18N["home.move"] = {
  "en": "We move with you", "es": "Nos movemos contigo", "fr": "Nous bougeons avec vous", "ar": "نتنقل معك",
  "pt": "Nós nos movemos com você", "ur": "Hum aapke saath chalte hain", "hi": "हम आपके साथ चलते हैं", "bn": "আমরা আপনার সঙ্গে চলি",
  "ud": "ہم آپ کے ساتھ چلتے ہیں", "zh": "我们与您同行", "de": "Wir bewegen uns mit Ihnen", "it": "Ci muoviamo con te",
  "ru": "Мы движемся вместе с вами", "tr": "Sizinle birlikte hareket ediyoruz", "ko": "고객님과 함께 움직입니다", "ja": "お客様とともに移動します",
  "vi": "Chúng tôi di chuyển cùng bạn", "fa": "ما با شما حرکت می‌کنیم", "th": "เราเคลื่อนที่ไปกับคุณ"
};

NOEL_I18N["home.gold"] = {
  "en": "The gold standard of private travel.", "es": "El estándar de oro del viaje privado.", "fr": "La référence du voyage privé.", "ar": "المعيار الذهبي للسفر الخاص.",
  "pt": "O padrão ouro da viagem privada.", "ur": "Private travel ka gold standard.", "hi": "निजी यात्रा का स्वर्ण मानक।", "bn": "ব্যক্তিগত ভ্রমণের স্বর্ণমান।",
  "ud": "نجی سفر کا سنہری معیار", "zh": "私人出行的黄金标准。", "de": "Der Goldstandard des privaten Reisens.", "it": "Lo standard d'oro del viaggio privato.",
  "ru": "Золотой стандарт частных поездок.", "tr": "Özel seyahatin altın standardı.", "ko": "프라이빗 이동의 골드 스탠더드.", "ja": "プライベート旅行のゴールドスタンダード。",
  "vi": "Tiêu chuẩn vàng của du lịch riêng tư.", "fa": "استاندارد طلایی سفر خصوصی", "th": "มาตรฐานทองคำของการเดินทางส่วนตัว"
};

NOEL_I18N["home.gold_intro"] = {
  "en": "Our hand-selected chauffeurs prioritise your schedule, route, and comfort, ensuring you arrive refreshed for what matters.", "es": "Nuestros chóferes seleccionados a mano priorizan tu horario, tu ruta y tu comodidad, para que llegues fresco a lo que importa.", "fr": "Nos chauffeurs sélectionnés avec soin privilégient votre emploi du temps, votre itinéraire et votre confort, pour que vous arriviez reposé là où cela compte.", "ar": "سائقونا المختارون بعناية يعطون الأولوية لجدولك وطريقك وراحتك، لتصل منتعشًا لما يهمك.",
  "pt": "Nossos motoristas selecionados a dedo priorizam sua agenda, sua rota e seu conforto, para que você chegue descansado ao que importa.", "ur": "Hamare haath se chune hue chauffeurs aapke time, route aur aaram ko pehle rakhte hain, taaki aap taaza hoke pahunchen jahan zaroori hai.", "hi": "हमारे हाथ से चुने हुए शॉफ़र आपके समय, मार्ग और आराम को प्राथमिकता देते हैं, ताकि आप तरोताज़ा होकर पहुँचें जहाँ ज़रूरी है।", "bn": "আমাদের হাতে বাছা শোফাররা আপনার সময়, রুট ও আরামকে অগ্রাধিকার দেন, যাতে আপনি যা গুরুত্বপূর্ণ সেখানে সতেজ হয়ে পৌঁছান।",
  "ud": "ہمارے منتخب ڈرائیور آپ کے شیڈول، راستے اور آرام کا خیال رکھتے ہیں تاکہ آپ تازہ دم پہنچیں", "zh": "我们精心挑选的司机以您的时间表、路线和舒适为先，确保您精神饱满地到达。", "de": "Unsere handverlesenen Chauffeure richten sich nach Ihrem Zeitplan, Ihrer Route und Ihrem Komfort, damit Sie erfrischt ankommen.", "it": "I nostri chauffeur selezionati danno priorità ai tuoi orari, al percorso e al comfort, per farti arrivare riposato.",
  "ru": "Наши тщательно отобранные шофёры ставят на первое место ваше расписание, маршрут и комфорт, чтобы вы прибыли отдохнувшими.", "tr": "Özenle seçilmiş şoförlerimiz programınıza, rotanıza ve konforunuza öncelik verir, böylece dinlenmiş olarak varırsınız.", "ko": "엄선된 쇼퍼가 고객님의 일정, 경로, 편안함을 최우선으로 하여 상쾌하게 도착하실 수 있도록 합니다.", "ja": "厳選されたショファーがお客様のスケジュール、ルート、快適さを最優先し、リフレッシュして到着できるようにします。",
  "vi": "Tài xế được tuyển chọn kỹ lưỡng của chúng tôi ưu tiên lịch trình, lộ trình và sự thoải mái của bạn, đảm bảo bạn đến nơi sảng khoái.", "fa": "راننده‌های منتخب ما به برنامه، مسیر و راحتی شما اهمیت می‌دهند تا سرحال برسید", "th": "คนขับที่คัดสรรมาอย่างดีของเราให้ความสำคัญกับตาราง เส้นทาง และความสะดวกสบายของคุณ เพื่อให้คุณมาถึงอย่างสดชื่น"
};

NOEL_I18N["home.available"] = {
  "en": "Available 24/7", "es": "Disponible 24/7", "fr": "Disponible 24 h/24, 7 j/7", "ar": "متاح على مدار الساعة",
  "pt": "Disponível 24/7", "ur": "24/7 available", "hi": "24/7 उपलब्ध", "bn": "২৪/৭ উপলব্ধ",
  "ud": "24/7 دستیاب", "zh": "全天候可用", "de": "Rund um die Uhr verfügbar", "it": "Disponibile 24/7",
  "ru": "Доступно 24/7", "tr": "7/24 Kullanılabilir", "ko": "24시간 이용 가능", "ja": "24時間利用可能",
  "vi": "Hoạt động 24/7", "fa": "۲۴/۷ در دسترس", "th": "พร้อมให้บริการ 24/7"
};

NOEL_I18N["home.available_p"] = {
  "en": "Book anytime, anywhere.", "es": "Reserva cuando quieras, donde quieras.", "fr": "Réservez à tout moment, partout.", "ar": "احجز في أي وقت ومن أي مكان.",
  "pt": "Reserve a qualquer hora, em qualquer lugar.", "ur": "Kabhi bhi, kahin se bhi book karen.", "hi": "कभी भी, कहीं से भी बुक करें।", "bn": "যেকোনো সময়, যেকোনো জায়গা থেকে বুক করুন।",
  "ud": "کسی بھی وقت، کہیں بھی بک کریں", "zh": "随时随地预订。", "de": "Buchen Sie jederzeit und überall.", "it": "Prenota quando vuoi, ovunque.",
  "ru": "Бронируйте в любое время и в любом месте.", "tr": "İstediğiniz zaman, her yerde rezervasyon yapın.", "ko": "언제 어디서나 예약하세요.", "ja": "いつでも、どこでも予約できます。",
  "vi": "Đặt xe bất cứ lúc nào, ở bất cứ đâu.", "fa": "در هر زمان، هر کجا رزرو کنید", "th": "จองได้ทุกเวลา ทุกที่"
};

NOEL_I18N["home.flight_number"] = {
  "en": "Flight number", "es": "Número de vuelo", "fr": "Numéro de vol", "ar": "رقم الرحلة",
  "pt": "Número do voo", "ur": "Flight number", "hi": "फ़्लाइट नंबर", "bn": "ফ্লাইট নম্বর",
  "ud": "فلائٹ نمبر", "zh": "航班号", "de": "Flugnummer", "it": "Numero di volo",
  "ru": "Номер рейса", "tr": "Uçuş numarası", "ko": "항공편 번호", "ja": "便名",
  "vi": "Số hiệu chuyến bay", "fa": "شمارهٔ پرواز", "th": "หมายเลขเที่ยวบิน"
};

NOEL_I18N["home.flight_p"] = {
  "en": "We adjust to your schedule.", "es": "Nos adaptamos a tu horario.", "fr": "Nous nous adaptons à votre emploi du temps.", "ar": "نتكيف مع جدولك.",
  "pt": "Nos adaptamos à sua agenda.", "ur": "Hum aapke schedule ke hisaab se adjust karte hain.", "hi": "हम आपके कार्यक्रम के अनुसार ढल जाते हैं।", "bn": "আমরা আপনার সময়সূচি অনুযায়ী মানিয়ে নিই।",
  "ud": "ہم آپ کے شیڈول کے مطابق ڈھل جاتے ہیں", "zh": "我们会根据您的时间表调整。", "de": "Wir passen uns Ihrem Zeitplan an.", "it": "Ci adattiamo ai tuoi orari.",
  "ru": "Мы подстраиваемся под ваше расписание.", "tr": "Programınıza uyum sağlıyoruz.", "ko": "고객님의 일정에 맞춥니다.", "ja": "お客様のスケジュールに合わせます。",
  "vi": "Chúng tôi điều chỉnh theo lịch trình của bạn.", "fa": "ما با برنامهٔ شما سازگار می‌شویم", "th": "เราปรับตามตารางของคุณ"
};

NOEL_I18N["home.fleet"] = {
  "en": "Diverse Fleet", "es": "Flota variada", "fr": "Flotte variée", "ar": "أسطول متنوع",
  "pt": "Frota diversificada", "ur": "Diverse Fleet", "hi": "विविध बेड़ा", "bn": "বৈচিত্র্যময় বহর",
  "ud": "متنوع فلیٹ", "zh": "多样化车队", "de": "Vielfältige Flotte", "it": "Flotta varia",
  "ru": "Разнообразный автопарк", "tr": "Çeşitli Filo", "ko": "다양한 차량", "ja": "多様な車両",
  "vi": "Đội xe đa dạng", "fa": "ناوگان متنوع", "th": "กองรถหลากหลาย"
};

NOEL_I18N["home.fleet_p"] = {
  "en": "From executive sedans to spacious SUVs.", "es": "Desde berlinas ejecutivas hasta SUV espaciosos.", "fr": "Des berlines exécutives aux SUV spacieux.", "ar": "من سيارات السيدان التنفيذية إلى سيارات الدفع الرباعي الواسعة.",
  "pt": "De sedãs executivos a SUVs espaçosos.", "ur": "Executive sedans se le kar spacious SUVs tak.", "hi": "एग्ज़ीक्यूटिव सेडान से लेकर विशाल SUV तक।", "bn": "এক্সিকিউটিভ সেডান থেকে প্রশস্ত SUV পর্যন্ত।",
  "ud": "ایگزیکٹو سیڈان سے لے کر وسیع SUV تک", "zh": "从行政轿车到宽敞 SUV。", "de": "Von Executive-Limousinen bis zu geräumigen SUVs.", "it": "Dalle berline executive ai SUV spaziosi.",
  "ru": "От представительских седанов до просторных внедорожников.", "tr": "Yönetici sedanlarından geniş SUV'lere.", "ko": "임원용 세단부터 넓은 SUV까지.", "ja": "エグゼクティブセダンから広々としたSUVまで。",
  "vi": "Từ sedan điều hành đến SUV rộng rãi.", "fa": "از سدان اجرایی تا SUV جادار", "th": "ตั้งแต่รถเก๋งผู้บริหารไปจนถึง SUV กว้างขวาง"
};

NOEL_I18N["foot.tagline"] = {
  "en": "Luxury Chauffeur Rides Across USA — premium chauffeur service, on-time pickups, clear communication.", "es": "Viajes de lujo con chófer en todo EE. UU.: servicio premium, recogidas puntuales y comunicación clara.", "fr": "Trajets de luxe avec chauffeur partout aux États-Unis — service premium, prises en charge à l'heure et communication claire.", "ar": "رحلات فاخرة مع سائق في جميع أنحاء الولايات المتحدة — خدمة مميزة واستلام في الوقت المحدد وتواصل واضح.",
  "pt": "Viagens de luxo com motorista em todos os EUA — serviço premium, embarques pontuais e comunicação clara.", "ur": "USA bhar mein luxury chauffeur rides — premium service, waqt par pickups, saaf communication.", "hi": "पूरे अमेरिका में लग्ज़री शॉफ़र सवारी — प्रीमियम सेवा, समय पर पिकअप, स्पष्ट संवाद।", "bn": "সারা যুক্তরাষ্ট্রজুড়ে বিলাসবহুল শোফার রাইড — প্রিমিয়াম পরিষেবা, সময়মতো পিকআপ, পরিষ্কার যোগাযোগ।",
  "ud": "پورے امریکہ میں عیش و آرام کے ساتھ ڈرائیور کی سہولت — پریمیم ڈرائیور سروس، وقت پر پک اپ، واضح مواصلات", "zh": "美国各地豪华专车服务——高端专车服务、准时接送、沟通清晰。", "de": "Luxuriöse Chauffeurfahrten in den USA — Premium-Chauffeurservice, pünktliche Abholungen, klare Kommunikation.", "it": "Corse di lusso con chauffeur in tutti gli USA — servizio chauffeur premium, ritiri puntuali, comunicazione chiara.",
  "ru": "Роскошные поездки с шофёром по всем США — премиальный сервис шофёров, пунктуальная подача, чёткая коммуникация.", "tr": "ABD Genelinde Lüks Şoförlü Yolculuklar — premium şoför hizmeti, zamanında biniş, net iletişim.", "ko": "미국 전역 럭셔리 쇼퍼 이동 — 프리미엄 쇼퍼 서비스, 정시 픽업, 명확한 소통.", "ja": "全米の高級ショファー乗車 — プレミアムショファーサービス、時間通りの乗車、明確なコミュニケーション。",
  "vi": "Chuyến xe sang trọng có tài xế trên khắp Hoa Kỳ — dịch vụ tài xế cao cấp, đón đúng giờ, liên lạc rõ ràng.", "fa": "سفر لوکس با راننده در سراسر ایالات متحده — خدمات رانندهٔ ممتاز، سوارشدن سر وقت، ارتباط شفاف", "th": "การเดินทางหรูพร้อมคนขับทั่วสหรัฐอเมริกา — บริการคนขับระดับพรีเมียม รับตรงเวลา สื่อสารชัดเจน"
};

NOEL_I18N["foot.hourly"] = {
  "en": "Hourly", "es": "Por horas", "fr": "À l'heure", "ar": "بالساعة",
  "pt": "Por hora", "ur": "Hourly", "hi": "घंटे के हिसाब से", "bn": "ঘণ্টা হিসেবে",
  "ud": "فی گھنٹہ", "zh": "按小时", "de": "Stundenweise", "it": "A ore",
  "ru": "Почасовая аренда", "tr": "Saatlik", "ko": "시간제", "ja": "時間貸し",
  "vi": "Theo giờ", "fa": "ساعتی", "th": "รายชั่วโมง"
};

NOEL_I18N["foot.corporate"] = {
  "en": "Corporate", "es": "Corporativo", "fr": "Entreprises", "ar": "للشركات",
  "pt": "Corporativo", "ur": "Corporate", "hi": "कॉर्पोरेट", "bn": "কর্পোরেট",
  "ud": "کارپوریٹ", "zh": "企业", "de": "Unternehmen", "it": "Aziende",
  "ru": "Корпоративным клиентам", "tr": "Kurumsal", "ko": "기업", "ja": "法人",
  "vi": "Doanh nghiệp", "fa": "شرکتی", "th": "องค์กร"
};

NOEL_I18N["foot.wedding"] = {
  "en": "Wedding", "es": "Bodas", "fr": "Mariage", "ar": "زفاف",
  "pt": "Casamento", "ur": "Wedding", "hi": "विवाह", "bn": "বিয়ে",
  "ud": "شادی", "zh": "婚礼", "de": "Hochzeit", "it": "Matrimonio",
  "ru": "Свадьба", "tr": "Düğün", "ko": "웨딩", "ja": "ウェディング",
  "vi": "Đám cưới", "fa": "عروسی", "th": "งานแต่งงาน"
};

NOEL_I18N["foot.jfk_transfers"] = {
  "en": "JFK Airport Transfers", "es": "Traslados al aeropuerto JFK", "fr": "Transferts aéroport JFK", "ar": "النقل من وإلى مطار JFK",
  "pt": "Transfers do aeroporto JFK", "ur": "JFK Airport Transfers", "hi": "JFK एयरपोर्ट ट्रांसफर", "bn": "JFK বিমানবন্দর ট্রান্সফার",
  "ud": "JFK ہوائی اڈے کی منتقلی", "zh": "JFK 机场接送", "de": "JFK-Flughafentransfers", "it": "Trasferimenti aeroporto JFK",
  "ru": "Трансферы в аэропорт JFK", "tr": "JFK Havalimanı Transferleri", "ko": "JFK 공항 이동", "ja": "JFK空港送迎",
  "vi": "Đưa đón Sân bay JFK", "fa": "ترانسفر فرودگاه JFK", "th": "รับส่งสนามบิน JFK"
};

NOEL_I18N["foot.lga_transfers"] = {
  "en": "LaGuardia Airport Transfers", "es": "Traslados al aeropuerto LaGuardia", "fr": "Transferts aéroport LaGuardia", "ar": "النقل من وإلى مطار LaGuardia",
  "pt": "Transfers do aeroporto LaGuardia", "ur": "LaGuardia Airport Transfers", "hi": "LaGuardia एयरपोर्ट ट्रांसफर", "bn": "LaGuardia বিমানবন্দর ট্রান্সফার",
  "ud": "LaGuardia ہوائی اڈے کی منتقلی", "zh": "拉瓜迪亚机场接送", "de": "LaGuardia-Flughafentransfers", "it": "Trasferimenti aeroporto LaGuardia",
  "ru": "Трансферы в аэропорт Ла-Гуардия", "tr": "LaGuardia Havalimanı Transferleri", "ko": "라과디아 공항 이동", "ja": "ラガーディア空港送迎",
  "vi": "Đưa đón Sân bay LaGuardia", "fa": "ترانسفر فرودگاه LaGuardia", "th": "รับส่งสนามบิน LaGuardia"
};

NOEL_I18N["foot.ewr_transfers"] = {
  "en": "Newark Airport Transfers", "es": "Traslados al aeropuerto Newark", "fr": "Transferts aéroport Newark", "ar": "النقل من وإلى مطار Newark",
  "pt": "Transfers do aeroporto Newark", "ur": "Newark Airport Transfers", "hi": "Newark एयरपोर्ट ट्रांसफर", "bn": "Newark বিমানবন্দর ট্রান্সফার",
  "ud": "نیوارک ہوائی اڈے کی منتقلی", "zh": "纽瓦克机场接送", "de": "Newark-Flughafentransfers", "it": "Trasferimenti aeroporto di Newark",
  "ru": "Трансферы в аэропорт Ньюарк", "tr": "Newark Havalimanı Transferleri", "ko": "뉴어크 공항 이동", "ja": "ニューアーク空港送迎",
  "vi": "Đưa đón Sân bay Newark", "fa": "ترانسفر فرودگاه نیوآرک", "th": "รับส่งสนามบินนวร์ก"
};

NOEL_I18N["foot.teb_transfers"] = {
  "en": "Teterboro Airport Transfers", "es": "Traslados al aeropuerto Teterboro", "fr": "Transferts aéroport Teterboro", "ar": "النقل من وإلى مطار Teterboro",
  "pt": "Transfers do aeroporto Teterboro", "ur": "Teterboro Airport Transfers", "hi": "Teterboro एयरपोर्ट ट्रांसफर", "bn": "Teterboro বিমানবন্দর ট্রান্সফার",
  "ud": "Teterboro ہوائی اڈے کی منتقلی", "zh": "泰特伯勒机场接送", "de": "Teterboro-Flughafentransfers", "it": "Trasferimenti aeroporto di Teterboro",
  "ru": "Трансферы в аэропорт Тетерборо", "tr": "Teterboro Havalimanı Transferleri", "ko": "테터보로 공항 이동", "ja": "テターボロ空港送迎",
  "vi": "Đưa đón Sân bay Teterboro", "fa": "ترانسفر فرودگاه Teterboro", "th": "รับส่งสนามบิน Teterboro"
};

NOEL_I18N["foot.guide_jfk_vs"] = {
  "en": "JFK vs LaGuardia vs Newark", "es": "JFK frente a LaGuardia frente a Newark", "fr": "JFK vs LaGuardia vs Newark", "ar": "JFK مقابل LaGuardia مقابل Newark",
  "pt": "JFK vs LaGuardia vs Newark", "ur": "JFK vs LaGuardia vs Newark", "hi": "JFK बनाम LaGuardia बनाम Newark", "bn": "JFK বনাম LaGuardia বনাম Newark",
  "ud": "JFK بمقابلہ LaGuardia بمقابلہ Newark", "zh": "JFK 与拉瓜迪亚与纽瓦克对比", "de": "JFK vs. LaGuardia vs. Newark", "it": "JFK vs LaGuardia vs Newark",
  "ru": "JFK vs Ла-Гуардия vs Ньюарк", "tr": "JFK, LaGuardia ve Newark karşılaştırması", "ko": "JFK vs 라과디아 vs 뉴어크", "ja": "JFK vs ラガーディア vs ニューアーク",
  "vi": "JFK và LaGuardia và Newark", "fa": "JFK در برابر LaGuardia در برابر Newark", "th": "JFK เทียบกับ LaGuardia เทียบกับ Newark"
};

NOEL_I18N["foot.guide_blackcar"] = {
  "en": "Black car vs Uber Black", "es": "Coche negro frente a Uber Black", "fr": "Voiture noire vs Uber Black", "ar": "السيارة السوداء مقابل Uber Black",
  "pt": "Carro preto vs Uber Black", "ur": "Black car vs Uber Black", "hi": "ब्लैक कार बनाम Uber Black", "bn": "ব্ল্যাক কার বনাম Uber Black",
  "ud": "بلیک کار بمقابلہ Uber Black", "zh": "专车与 Uber Black 对比", "de": "Black Car vs. Uber Black", "it": "Black car vs Uber Black",
  "ru": "Чёрный автомобиль vs Uber Black", "tr": "Black car ve Uber Black karşılaştırması", "ko": "블랙카 vs Uber Black", "ja": "ブラックカー vs Uber Black",
  "vi": "Xe black car và Uber Black", "fa": "بلک‌کار در برابر Uber Black", "th": "รถ black car เทียบกับ Uber Black"
};

NOEL_I18N["foot.guide_jfk_terminal"] = {
  "en": "JFK terminal pickup guide", "es": "Guía de recogida en la terminal de JFK", "fr": "Guide de prise en charge au terminal JFK", "ar": "دليل الاستلام من صالة JFK",
  "pt": "Guia de embarque no terminal JFK", "ur": "JFK terminal pickup guide", "hi": "JFK टर्मिनल पिकअप गाइड", "bn": "JFK টার্মিনাল পিকআপ গাইড",
  "ud": "JFK ٹرمینل پک اپ گائیڈ", "zh": "JFK 航站楼接送指南", "de": "Abholguide für das JFK-Terminal", "it": "Guida al ritiro al terminal JFK",
  "ru": "Гид по подаче в терминале JFK", "tr": "JFK terminal biniş rehberi", "ko": "JFK 터미널 픽업 가이드", "ja": "JFKターミナル乗車ガイド",
  "vi": "Hướng dẫn đón tại nhà ga JFK", "fa": "راهنمای سوارشدن در ترمینال JFK", "th": "คู่มือการรับที่อาคารผู้โดยสาร JFK"
};

NOEL_I18N["foot.guide_how_much"] = {
  "en": "How much is a black car in NYC?", "es": "¿Cuánto cuesta un coche negro en Nueva York?", "fr": "Combien coûte une voiture noire à New York ?", "ar": "كم تكلفة السيارة السوداء في نيويورك؟",
  "pt": "Quanto custa um carro preto em Nova York?", "ur": "NYC mein black car kitne ki hai?", "hi": "NYC में ब्लैक कार कितने की है?", "bn": "NYC-তে ব্ল্যাক কার কত?",
  "ud": "نیویارک سٹی میں بلیک کار کی قیمت کتنی ہے؟", "zh": "在纽约叫一辆专车要多少钱？", "de": "Wie viel kostet ein Black Car in NYC?", "it": "Quanto costa una black car a New York?",
  "ru": "Сколько стоит чёрный автомобиль в Нью-Йорке?", "tr": "New York'ta black car ne kadar?", "ko": "뉴욕에서 블랙카는 얼마인가요?", "ja": "NYCでブラックカーはいくらですか？",
  "vi": "Xe black car ở NYC giá bao nhiêu?", "fa": "بلک‌کار در نیویورک سیتی چقدر هزینه دارد؟", "th": "รถ black car ในนิวยอร์กซิตี้ราคาเท่าไร?"
};

NOEL_I18N["foot.all_guides"] = {
  "en": "All guides", "es": "Todas las guías", "fr": "Tous les guides", "ar": "كل الأدلة",
  "pt": "Todos os guias", "ur": "Saare guides", "hi": "सभी गाइड", "bn": "সব গাইড",
  "ud": "تمام رہنما", "zh": "所有指南", "de": "Alle Guides", "it": "Tutte le guide",
  "ru": "Все гиды", "tr": "Tüm rehberler", "ko": "모든 가이드", "ja": "すべてのガイド",
  "vi": "Tất cả hướng dẫn", "fa": "همهٔ راهنماها", "th": "คู่มือทั้งหมด"
};

NOEL_I18N["foot.about"] = {
  "en": "Premium chauffeur service across the USA. On-time pickups, calm and comfortable rides.", "es": "Servicio premium de chófer en todo EE. UU. Recogidas puntuales, viajes tranquilos y cómodos.", "fr": "Service de chauffeur premium partout aux États-Unis. Prises en charge à l'heure, trajets calmes et confortables.", "ar": "خدمة سائق مميزة في جميع أنحاء الولايات المتحدة. استلام في الوقت المحدد ورحلات هادئة ومريحة.",
  "pt": "Serviço premium de motorista em todos os EUA. Embarques pontuais, viagens calmas e confortáveis.", "ur": "USA bhar mein premium chauffeur service. Waqt par pickups, aaramdeh aur sakoon wali rides.", "hi": "पूरे अमेरिका में प्रीमियम शॉफ़र सेवा। समय पर पिकअप, शांत और आरामदायक सवारी।", "bn": "সারা যুক্তরাষ্ট্রজুড়ে প্রিমিয়াম শোফার পরিষেবা। সময়মতো পিকআপ, শান্ত ও আরামদায়ক রাইড।",
  "ud": "پورے امریکہ میں پریمیم ڈرائیور سروس، وقت پر پک اپ، پرسکون اور آرام دہ سواری", "zh": "美国各地的高端专车服务。准时接送，行程安静舒适。", "de": "Premium-Chauffeurservice in den USA. Pünktliche Abholungen, ruhige und komfortable Fahrten.", "it": "Servizio chauffeur premium in tutti gli USA. Ritiri puntuali, corse tranquille e confortevoli.",
  "ru": "Премиальный сервис шофёров по всем США. Пунктуальная подача, спокойные и комфортабельные поездки.", "tr": "ABD genelinde premium şoför hizmeti. Zamanında biniş, sakin ve konforlu yolculuklar.", "ko": "미국 전역 프리미엄 쇼퍼 서비스. 정시 픽업, 차분하고 편안한 이동.", "ja": "全米のプレミアムショファーサービス。時間通りの乗車、落ち着いた快適な乗車。",
  "vi": "Dịch vụ tài xế cao cấp trên khắp Hoa Kỳ. Đón đúng giờ, chuyến đi yên tĩnh và thoải mái.", "fa": "خدمات رانندهٔ ممتاز در سراسر ایالات متحده، سوارشدن سر وقت، سواری آرام و راحت", "th": "บริการคนขับระดับพรีเมียมทั่วสหรัฐอเมริกา รับตรงเวลา การเดินทางสงบและสะดวกสบาย"
};

NOEL_I18N["foot.airport_transfers"] = {
  "en": "Airport transfers", "es": "Traslados al aeropuerto", "fr": "Transferts aéroport", "ar": "النقل من وإلى المطار",
  "pt": "Transfers de aeroporto", "ur": "Airport transfers", "hi": "एयरपोर्ट ट्रांसफर", "bn": "বিমানবন্দর ট্রান্সফার",
  "ud": "ہوائی اڈے کی منتقلی", "zh": "机场接送", "de": "Flughafentransfers", "it": "Trasferimenti aeroportuali",
  "ru": "Трансферы в аэропорт", "tr": "Havalimanı transferleri", "ko": "공항 이동", "ja": "空港送迎",
  "vi": "Đưa đón sân bay", "fa": "ترانسفر فرودگاه", "th": "รับส่งสนามบิน"
};

NOEL_I18N["foot.where"] = {
  "en": "Where we drive", "es": "Dónde conducimos", "fr": "Où nous conduisons", "ar": "أين نقود",
  "pt": "Onde dirigimos", "ur": "Hum kahan drive karte hain", "hi": "हम कहाँ ड्राइव करते हैं", "bn": "আমরা কোথায় গাড়ি চালাই",
  "ud": "ہم کہاں چلاتے ہیں", "zh": "我们的服务地区", "de": "Wo wir fahren", "it": "Dove guidiamo",
  "ru": "Где мы работаем", "tr": "Nereye gidiyoruz", "ko": "운행 지역", "ja": "運行エリア",
  "vi": "Nơi chúng tôi phục vụ", "fa": "ما کجا رانندگی می‌کنیم", "th": "เราขับไปที่ไหน"
};

NOEL_I18N["foot.guides"] = {
  "en": "Guides", "es": "Guías", "fr": "Guides", "ar": "أدلة",
  "pt": "Guias", "ur": "Guides", "hi": "गाइड", "bn": "গাইড",
  "ud": "رہنما", "zh": "指南", "de": "Guides", "it": "Guide",
  "ru": "Гиды", "tr": "Rehberler", "ko": "가이드", "ja": "ガイド",
  "vi": "Hướng dẫn", "fa": "راهنماها", "th": "คู่มือ"
};

NOEL_I18N["foot.services"] = {
  "en": "Services", "es": "Servicios", "fr": "Services", "ar": "الخدمات",
  "pt": "Serviços", "ur": "Services", "hi": "सेवाएँ", "bn": "পরিষেবা",
  "ud": "خدمات", "zh": "服务", "de": "Dienstleistungen", "it": "Servizi",
  "ru": "Услуги", "tr": "Hizmetler", "ko": "서비스", "ja": "サービス",
  "vi": "Dịch vụ", "fa": "خدمات", "th": "บริการ"
};

NOEL_I18N["foot.company"] = {
  "en": "Company", "es": "Empresa", "fr": "Entreprise", "ar": "الشركة",
  "pt": "Empresa", "ur": "Company", "hi": "कंपनी", "bn": "কোম্পানি",
  "ud": "کمپنی", "zh": "公司", "de": "Unternehmen", "it": "Azienda",
  "ru": "Компания", "tr": "Şirket", "ko": "회사", "ja": "会社",
  "vi": "Công ty", "fa": "شرکت", "th": "บริษัท"
};

NOEL_I18N["foot.drive_with_us"] = {
  "en": "Drive with us", "es": "Conduce con nosotros", "fr": "Conduisez avec nous", "ar": "قُد معنا",
  "pt": "Dirija conosco", "ur": "Hamare saath drive karen", "hi": "हमारे साथ ड्राइव करें", "bn": "আমাদের সঙ্গে গাড়ি চালান",
  "ud": "ہمارے ساتھ ڈرائیو کریں", "zh": "加入我们开车", "de": "Fahren Sie mit uns", "it": "Guida con noi",
  "ru": "Работайте с нами", "tr": "Bizimle sürün", "ko": "함께 운전하기", "ja": "私たちと一緒に運転する",
  "vi": "Lái xe cùng chúng tôi", "fa": "با ما رانندگی کنید", "th": "ขับรถกับเรา"
};

NOEL_I18N["foot.app"] = {
  "en": "App", "es": "App", "fr": "App", "ar": "التطبيق",
  "pt": "App", "ur": "App", "hi": "ऐप", "bn": "অ্যাপ",
  "ud": "ایپ", "zh": "应用", "de": "App", "it": "App",
  "ru": "Приложение", "tr": "Uygulama", "ko": "앱", "ja": "アプリ",
  "vi": "Ứng dụng", "fa": "برنامه", "th": "แอป"
};

NOEL_I18N["foot.privacy"] = {
  "en": "Privacy Policy", "es": "Política de privacidad", "fr": "Politique de confidentialité", "ar": "سياسة الخصوصية",
  "pt": "Política de Privacidade", "ur": "Privacy Policy", "hi": "गोपनीयता नीति", "bn": "গোপনীয়তা নীতি",
  "ud": "پرائیویسی پالیسی", "zh": "隐私政策", "de": "Datenschutzerklärung", "it": "Informativa sulla privacy",
  "ru": "Политика конфиденциальности", "tr": "Gizlilik Politikası", "ko": "개인정보처리방침", "ja": "プライバシーポリシー",
  "vi": "Chính sách bảo mật", "fa": "سیاست حفظ حریم خصوصی", "th": "นโยบายความเป็นส่วนตัว"
};

NOEL_I18N["foot.terms"] = {
  "en": "Terms", "es": "Términos", "fr": "Conditions", "ar": "الشروط",
  "pt": "Termos", "ur": "Terms", "hi": "शर्तें", "bn": "শর্তাবলী",
  "ud": "شرائط", "zh": "条款", "de": "Bedingungen", "it": "Termini",
  "ru": "Условия", "tr": "Koşullar", "ko": "약관", "ja": "利用規約",
  "vi": "Điều khoản", "fa": "شرایط", "th": "ข้อกำหนด"
};

NOEL_I18N["foot.hourly_hire"] = {
  "en": "Hourly hire", "es": "Alquiler por horas", "fr": "Location à l'heure", "ar": "الحجز بالساعة",
  "pt": "Aluguel por hora", "ur": "Hourly hire", "hi": "घंटे के हिसाब से किराया", "bn": "ঘণ্টা হিসেবে ভাড়া",
  "ud": "فی گھنٹہ کرایہ", "zh": "按小时租用", "de": "Stundenweise Miete", "it": "Noleggio a ore",
  "ru": "Почасовая аренда", "tr": "Saatlik kiralama", "ko": "시간제 대여", "ja": "時間貸し",
  "vi": "Thuê theo giờ", "fa": "کرایهٔ ساعتی", "th": "เช่ารายชั่วโมง"
};

NOEL_I18N["foot.corporate_travel"] = {
  "en": "Corporate travel", "es": "Viajes corporativos", "fr": "Voyages d'affaires", "ar": "سفر الشركات",
  "pt": "Viagens corporativas", "ur": "Corporate travel", "hi": "कॉर्पोरेट यात्रा", "bn": "কর্পোরেট ভ্রমণ",
  "ud": "کارپوریٹ سفر", "zh": "企业出行", "de": "Geschäftsreisen", "it": "Viaggi aziendali",
  "ru": "Деловые поездки", "tr": "Kurumsal seyahat", "ko": "기업 출장", "ja": "法人旅行",
  "vi": "Du lịch doanh nghiệp", "fa": "سفر شرکتی", "th": "การเดินทางธุรกิจ"
};

NOEL_I18N["foot.wedding_chauffeur"] = {
  "en": "Wedding chauffeur", "es": "Chófer para bodas", "fr": "Chauffeur de mariage", "ar": "سائق الزفاف",
  "pt": "Motorista de casamento", "ur": "Wedding chauffeur", "hi": "विवाह शॉफ़र", "bn": "বিয়ের শোফার",
  "ud": "شادی کا ڈرائیور", "zh": "婚礼司机", "de": "Hochzeits-Chauffeur", "it": "Chauffeur per matrimoni",
  "ru": "Шофёр на свадьбу", "tr": "Düğün şoförü", "ko": "웨딩 쇼퍼", "ja": "ウェディングショファー",
  "vi": "Tài xế đám cưới", "fa": "رانندهٔ عروسی", "th": "คนขับงานแต่งงาน"
};

NOEL_I18N["foot.point_to_point"] = {
  "en": "Point to point", "es": "De puerta a puerta", "fr": "Point à point", "ar": "من نقطة إلى نقطة",
  "pt": "Ponto a ponto", "ur": "Point to point", "hi": "पॉइंट टू पॉइंट", "bn": "পয়েন্ট টু পয়েন্ট",
  "ud": "پوائنٹ سے پوائنٹ", "zh": "点对点", "de": "Von Punkt zu Punkt", "it": "Da punto a punto",
  "ru": "Из точки в точку", "tr": "Noktadan noktaya", "ko": "지점 간 이동", "ja": "ポイントツーポイント",
  "vi": "Từ điểm này đến điểm khác", "fa": "نقطه‌به‌نقطه", "th": "จากจุดหนึ่งไปยังอีกจุดหนึ่ง"
};

NOEL_I18N["foot.reserved"] = {
  "en": "All rights reserved.", "es": "Todos los derechos reservados.", "fr": "Tous droits réservés.", "ar": "جميع الحقوق محفوظة.",
  "pt": "Todos os direitos reservados.", "ur": "All rights reserved.", "hi": "सर्वाधिकार सुरक्षित।", "bn": "সর্বস্বত্ব সংরক্ষিত।",
  "ud": "جملہ حقوق محفوظ ہیں", "zh": "版权所有。", "de": "Alle Rechte vorbehalten.", "it": "Tutti i diritti riservati.",
  "ru": "Все права защищены.", "tr": "Tüm hakları saklıdır.", "ko": "All rights reserved.", "ja": "All rights reserved.",
  "vi": "Đã đăng ký bản quyền.", "fa": "کلیهٔ حقوق محفوظ است", "th": "สงวนลิขสิทธิ์"
};

NOEL_I18N["foot.powered_by"] = {
  "en": "Powered by Noel Chauffer", "es": "Con la tecnología de Noel Chauffer", "fr": "Propulsé par Noel Chauffer", "ar": "مدعوم من نويل شوفير",
  "pt": "Desenvolvido por Noel Chauffer", "ur": "Powered by Noel Chauffer", "hi": "नोएल शॉफ़र द्वारा संचालित", "bn": "নোয়েল শোফার দ্বারা চালিত",
  "ud": "Noel Chauffer کے ذریعے چلتا ہے", "zh": "由 Noel Chauffer 提供", "de": "Bereitgestellt von Noel Chauffer", "it": "Offerto da Noel Chauffer",
  "ru": "Работает на Noel Chauffer", "tr": "Noel Chauffer tarafından sunulmaktadır", "ko": "Noel Chauffer 제공", "ja": "Noel Chauffer提供",
  "vi": "Được cung cấp bởi Noel Chauffer", "fa": "قدرت‌گرفته از Noel Chauffer", "th": "ขับเคลื่อนโดย Noel Chauffer"
};

NOEL_I18N["app.book"] = {
  "en": "Book", "es": "Reservar", "fr": "Réserver", "ar": "احجز",
  "pt": "Reservar", "ur": "Book karen", "hi": "बुक करें", "bn": "বুক করুন",
  "ud": "بک کریں", "zh": "预订", "de": "Buchen", "it": "Prenota",
  "ru": "Забронировать", "tr": "Rezervasyon Yap", "ko": "예약", "ja": "予約する",
  "vi": "Đặt xe", "fa": "رزرو کنید", "th": "จอง"
};

NOEL_I18N["app.tag"] = {
  "en": "Luxury Chauffeur Rides Across USA", "es": "Viajes de lujo con chófer en todo EE. UU.", "fr": "Trajets de luxe avec chauffeur partout aux États-Unis", "ar": "رحلات فاخرة مع سائق في جميع أنحاء الولايات المتحدة",
  "pt": "Viagens de luxo com motorista em todos os EUA", "ur": "USA bhar mein luxury chauffeur rides", "hi": "पूरे अमेरिका में लग्ज़री शॉफ़र सवारी", "bn": "সারা যুক্তরাষ্ট্রজুড়ে বিলাসবহুল শোফার রাইড",
  "ud": "پورے امریکہ میں عیش و آرام کے ساتھ ڈرائیور کی سہولت", "zh": "美国各地豪华专车服务", "de": "Luxuriöse Chauffeurfahrten in den USA", "it": "Corse di lusso con chauffeur in tutti gli USA",
  "ru": "Роскошные поездки с шофёром по всем США", "tr": "ABD Genelinde Lüks Şoförlü Yolculuklar", "ko": "미국 전역 럭셔리 쇼퍼 이동", "ja": "全米の高級ショファー乗車",
  "vi": "Chuyến xe sang trọng có tài xế trên khắp Hoa Kỳ", "fa": "سفر لوکس با راننده در سراسر ایالات متحده", "th": "การเดินทางหรูพร้อมคนขับทั่วสหรัฐอเมริกา"
};

NOEL_I18N["app.my_rides_heading"] = {
  "en": "My rides", "es": "Mis viajes", "fr": "Mes trajets", "ar": "رحلاتي",
  "pt": "Minhas viagens", "ur": "Meri rides", "hi": "मेरी सवारियाँ", "bn": "আমার রাইডগুলো",
  "ud": "میری سواریاں", "zh": "我的行程", "de": "Meine Fahrten", "it": "Le mie corse",
  "ru": "Мои поездки", "tr": "Yolculuklarım", "ko": "내 이동", "ja": "マイ乗車",
  "vi": "Chuyến đi của tôi", "fa": "سفرهای من", "th": "การเดินทางของฉัน"
};

NOEL_I18N["app.history_intro"] = {
  "en": "Enter the phone number you booked with to see your rides.", "es": "Escribe el número de teléfono con el que reservaste para ver tus viajes.", "fr": "Saisissez le numéro de téléphone utilisé pour réserver afin de voir vos trajets.", "ar": "أدخل رقم الهاتف الذي حجزت به لترى رحلاتك.",
  "pt": "Informe o número de telefone usado na reserva para ver suas viagens.", "ur": "Apni rides dekhne ke liye wo phone number likhen jis se book kiya tha.", "hi": "अपनी सवारियाँ देखने के लिए वह फ़ोन नंबर लिखें जिससे आपने बुक किया था।", "bn": "আপনার রাইড দেখতে যে ফোন নম্বর দিয়ে বুক করেছিলেন তা লিখুন।",
  "ud": "اپنی سواریاں دیکھنے کے لیے وہ فون نمبر درج کریں جو آپ نے بکنگ کے لیے استعمال کیا تھا", "zh": "输入您预订时使用的电话号码以查看您的行程。", "de": "Geben Sie die Telefonnummer ein, mit der Sie gebucht haben, um Ihre Fahrten zu sehen.", "it": "Inserisci il numero di telefono usato per la prenotazione per vedere le tue corse.",
  "ru": "Введите номер телефона, с которым вы бронировали, чтобы увидеть свои поездки.", "tr": "Yolculuklarınızı görmek için rezervasyon yaptığınız telefon numarasını girin.", "ko": "예약 시 사용한 전화번호를 입력하면 이동 내역을 볼 수 있습니다.", "ja": "予約時に使用した電話番号を入力すると、乗車履歴が表示されます。",
  "vi": "Nhập số điện thoại bạn đã dùng để đặt xe để xem các chuyến đi của bạn.", "fa": "برای مشاهدهٔ سفرهای خود، شماره تلفنی را که برای رزرو استفاده کرده‌اید وارد کنید", "th": "ป้อนหมายเลขโทรศัพท์ที่คุณใช้จองเพื่อดูการเดินทางของคุณ"
};

NOEL_I18N["app.signed_in_as"] = {
  "en": "Signed in as", "es": "Sesión iniciada como", "fr": "Connecté en tant que", "ar": "تم تسجيل الدخول باسم",
  "pt": "Conectado como", "ur": "Signed in as", "hi": "इस रूप में साइन इन किया गया", "bn": "হিসেবে সাইন ইন করা হয়েছে",
  "ud": "کے طور پر سائن ان", "zh": "登录身份", "de": "Angemeldet als", "it": "Accesso effettuato come",
  "ru": "Вы вошли как", "tr": "Şu kullanıcı olarak giriş yapıldı", "ko": "로그인 상태:", "ja": "サインイン中：",
  "vi": "Đã đăng nhập với tư cách", "fa": "واردشده به‌عنوان", "th": "เข้าสู่ระบบในชื่อ"
};

NOEL_I18N["app.showing_rides"] = {
  "en": "— showing your rides.", "es": "— mostrando tus viajes.", "fr": "— affichage de vos trajets.", "ar": "— عرض رحلاتك.",
  "pt": "— mostrando suas viagens.", "ur": "— aapki rides dikhayi ja rahi hain.", "hi": "— आपकी सवारियाँ दिखाई जा रही हैं।", "bn": "— আপনার রাইড দেখানো হচ্ছে।",
  "ud": "— آپ کی سواریاں دکھائی جا رہی ہیں", "zh": "— 正在显示您的行程。", "de": "— Ihre Fahrten werden angezeigt.", "it": "— ecco le tue corse.",
  "ru": "— показаны ваши поездки.", "tr": "— yolculuklarınız gösteriliyor.", "ko": "— 이동 내역을 표시하고 있습니다.", "ja": "— 乗車を表示しています。",
  "vi": "— đang hiển thị các chuyến đi của bạn.", "fa": "— سفرهای شما در حال نمایش است", "th": "— กำลังแสดงการเดินทางของคุณ"
};

NOEL_I18N["app.history_phone_ph"] = {
  "en": "Phone number used for booking", "es": "Número de teléfono usado para reservar", "fr": "Numéro de téléphone utilisé pour la réservation", "ar": "رقم الهاتف المستخدم للحجز",
  "pt": "Número de telefone usado na reserva", "ur": "Booking ke liye use kiya gaya phone number", "hi": "बुकिंग के लिए इस्तेमाल किया गया फ़ोन नंबर", "bn": "বুকিংয়ের জন্য ব্যবহৃত ফোন নম্বর",
  "ud": "بکنگ کے لیے استعمال کیا گیا فون نمبر", "zh": "预订时使用的电话号码", "de": "Telefonnummer, die für die Buchung verwendet wurde", "it": "Numero di telefono usato per la prenotazione",
  "ru": "Номер телефона, использованный при бронировании", "tr": "Rezervasyon için kullanılan telefon numarası", "ko": "예약에 사용한 전화번호", "ja": "予約に使用した電話番号",
  "vi": "Số điện thoại dùng để đặt xe", "fa": "شماره تلفن استفاده‌شده برای رزرو", "th": "หมายเลขโทรศัพท์ที่ใช้ในการจอง"
};

NOEL_I18N["app.show_rides"] = {
  "en": "Show my rides", "es": "Mostrar mis viajes", "fr": "Afficher mes trajets", "ar": "اعرض رحلاتي",
  "pt": "Mostrar minhas viagens", "ur": "Meri rides dikhayen", "hi": "मेरी सवारियाँ दिखाएँ", "bn": "আমার রাইড দেখান",
  "ud": "میری سواریاں دکھائیں", "zh": "显示我的行程", "de": "Meine Fahrten anzeigen", "it": "Mostra le mie corse",
  "ru": "Показать мои поездки", "tr": "Yolculuklarımı göster", "ko": "내 이동 보기", "ja": "マイ乗車を表示",
  "vi": "Hiển thị chuyến đi của tôi", "fa": "سفرهای من را نشان بده", "th": "แสดงการเดินทางของฉัน"
};

NOEL_I18N["app.all_rides"] = {
  "en": "← All rides", "es": "← Todos los viajes", "fr": "← Tous les trajets", "ar": "← كل الرحلات",
  "pt": "← Todas as viagens", "ur": "← Saari rides", "hi": "← सभी सवारियाँ", "bn": "← সব রাইড",
  "ud": "← تمام سواریاں", "zh": "← 所有行程", "de": "← Alle Fahrten", "it": "← Tutte le corse",
  "ru": "← Все поездки", "tr": "← Tüm yolculuklar", "ko": "← 모든 이동", "ja": "← すべての乗車",
  "vi": "← Tất cả chuyến đi", "fa": "← همهٔ سفرها", "th": "← การเดินทางทั้งหมด"
};

NOEL_I18N["app.support_intro"] = {
  "en": "We reply within 24 hours. Ask about booking, cancellation, waiting time, or a ride you have already booked.", "es": "Respondemos en un plazo de 24 horas. Pregunta sobre reservas, cancelación, tiempo de espera o un viaje que ya reservaste.", "fr": "Nous répondons sous 24 heures. Posez vos questions sur la réservation, l'annulation, le temps d'attente ou un trajet déjà réservé.", "ar": "نرد خلال 24 ساعة. اسأل عن الحجز أو الإلغاء أو وقت الانتظار أو رحلة حجزتها بالفعل.",
  "pt": "Respondemos em até 24 horas. Pergunte sobre reserva, cancelamento, tempo de espera ou uma viagem já reservada.", "ur": "Hum 24 hours ke andar reply karte hain. Booking, cancellation, waiting time, ya pehle se book ki hui ride ke baare mein poochhen.", "hi": "हम 24 घंटों के भीतर जवाब देते हैं। बुकिंग, रद्दीकरण, प्रतीक्षा समय, या पहले से बुक की गई सवारी के बारे में पूछें।", "bn": "আমরা ২৪ ঘণ্টার মধ্যে উত্তর দিই। বুকিং, বাতিল, অপেক্ষার সময়, বা ইতিমধ্যে বুক করা রাইড সম্পর্কে জিজ্ঞেস করুন।",
  "ud": "ہم 24 گھنٹوں کے اندر جواب دیتے ہیں۔ بکنگ، منسوخی، انتظار کے وقت، یا آپ کی پہلے سے بک کی گئی سواری کے بارے میں پوچھیں", "zh": "我们在24小时内回复。咨询预订、取消、等候时间或已预订的行程。", "de": "Wir antworten innerhalb von 24 Stunden. Fragen Sie nach Buchung, Stornierung, Wartezeit oder einer bereits gebuchten Fahrt.", "it": "Rispondiamo entro 24 ore. Chiedi di prenotazioni, cancellazioni, tempi di attesa o di una corsa già prenotata.",
  "ru": "Мы отвечаем в течение 24 часов. Спросите о бронировании, отмене, времени ожидания или о поездке, которую вы уже забронировали.", "tr": "24 saat içinde yanıt veriyoruz. Rezervasyon, iptal, bekleme süresi veya daha önce rezerve ettiğiniz bir yolculuk hakkında soru sorun.", "ko": "24시간 이내에 답변드립니다. 예약, 취소, 대기 시간 또는 이미 예약한 이동에 대해 문의하세요.", "ja": "24時間以内に返信します。予約、キャンセル、待ち時間、すでに予約済みの乗車についてお問い合わせください。",
  "vi": "Chúng tôi trả lời trong vòng 24 giờ. Hỏi về đặt xe, hủy xe, thời gian chờ, hoặc một chuyến đi bạn đã đặt.", "fa": "ما ظرف ۲۴ ساعت پاسخ می‌دهیم. دربارهٔ رزرو، لغو، زمان انتظار یا سفری که از قبل رزرو کرده‌اید بپرسید", "th": "เราตอบกลับภายใน 24 ชั่วโมง สอบถามเกี่ยวกับการจอง การยกเลิก เวลารอ หรือการเดินทางที่คุณจองไว้แล้ว"
};

NOEL_I18N["app.email_us"] = {
  "en": "You can also email us at", "es": "También puedes escribirnos a", "fr": "Vous pouvez aussi nous écrire à", "ar": "يمكنك أيضًا مراسلتنا على",
  "pt": "Você também pode nos enviar um e-mail para", "ur": "Aap hamein email bhi kar sakte hain:", "hi": "आप हमें इस पर भी ईमेल कर सकते हैं", "bn": "আপনি আমাদের ইমেইলও করতে পারেন",
  "ud": "آپ ہمیں اس پر ای میل بھی کر سکتے ہیں", "zh": "您也可以发送邮件至", "de": "Sie können uns auch per E-Mail erreichen unter", "it": "Puoi anche scriverci a",
  "ru": "Вы также можете написать нам на", "tr": "Bize şu adresten de e-posta gönderebilirsiniz", "ko": "이메일로도 문의하실 수 있습니다:", "ja": "メールでのお問い合わせはこちら",
  "vi": "Bạn cũng có thể gửi email cho chúng tôi tại", "fa": "همچنین می‌توانید به ما ایمیل بزنید", "th": "คุณยังสามารถส่งอีเมลหาเราได้ที่"
};

NOEL_I18N["foot.phone_label"] = {
  "en": "Phone:", "es": "Teléfono:", "fr": "Téléphone :", "ar": "الهاتف:",
  "pt": "Telefone:", "ur": "Phone:", "hi": "फ़ोन:", "bn": "ফোন:",
  "ud": "فون:", "zh": "电话：", "de": "Telefon:", "it": "Telefono:",
  "ru": "Телефон:", "tr": "Telefon:", "ko": "전화:", "ja": "電話：",
  "vi": "Điện thoại:", "fa": "تلفن:", "th": "โทรศัพท์:"
};

NOEL_I18N["foot.email_label"] = {
  "en": "Email:", "es": "Correo:", "fr": "E-mail :", "ar": "البريد الإلكتروني:",
  "pt": "E-mail:", "ur": "Email:", "hi": "ईमेल:", "bn": "ইমেইল:",
  "ud": "ای میل:", "zh": "邮箱：", "de": "E-Mail:", "it": "Email:",
  "ru": "Электронная почта:", "tr": "E-posta:", "ko": "이메일:", "ja": "メール：",
  "vi": "Email:", "fa": "ایمیل:", "th": "อีเมล:"
};

NOEL_I18N["form.flight_text"] = {
  "en": "Your chauffeur will meet you at the right terminal.", "es": "Tu chófer te recibirá en la terminal correcta.", "fr": "Votre chauffeur vous accueillera au bon terminal.", "ar": "سيستقبلك سائقك في الصالة الصحيحة.",
  "pt": "Seu motorista irá encontrá-lo no terminal correto.", "ur": "Aapka chauffeur aapko sahi terminal par milega.", "hi": "आपका चालक आपको सही टर्मिनल पर मिलेगा।", "bn": "আপনার চালক আপনাকে সঠিক টার্মিনালে স্বাগত জানাবেন।",
  "ud": "آپ کا ڈرائیور آپ سے صحیح ٹرمینل پر ملے گا", "zh": "您的司机将在正确的航站楼迎接您。", "de": "Ihr Chauffeur erwartet Sie am richtigen Terminal.", "it": "Il tuo chauffeur ti incontrerà al terminal giusto.",
  "ru": "Ваш шофёр встретит вас у нужного терминала.", "tr": "Şoförünüz sizi doğru terminalde karşılayacak.", "ko": "쇼퍼가 올바른 터미널에서 맞이합니다.", "ja": "ショファーが正しいターミナルでお迎えします。",
  "vi": "Tài xế của bạn sẽ gặp bạn tại nhà ga đúng.", "fa": "رانندهٔ شما در ترمینال صحیح با شما ملاقات می‌کند", "th": "คนขับของคุณจะพบคุณที่อาคารผู้โดยสารที่ถูกต้อง"
};

NOEL_I18N["form.ride_type"] = {
  "en": "Ride type", "es": "Tipo de viaje", "fr": "Type de trajet", "ar": "نوع الرحلة",
  "pt": "Tipo de viagem", "ur": "Ride type", "hi": "सवारी का प्रकार", "bn": "রাইডের ধরন",
  "ud": "سواری کی قسم", "zh": "行程类型", "de": "Fahrttyp", "it": "Tipo di corsa",
  "ru": "Тип поездки", "tr": "Yolculuk türü", "ko": "이동 종류", "ja": "乗車タイプ",
  "vi": "Loại chuyến đi", "fa": "نوع سفر", "th": "ประเภทการเดินทาง"
};

NOEL_I18N["form.by_hour"] = {
  "en": "By the hour", "es": "Por horas", "fr": "À l'heure", "ar": "بالساعة",
  "pt": "Por hora", "ur": "By the hour", "hi": "प्रति घंटा", "bn": "ঘণ্টা অনুযায়ী",
  "ud": "فی گھنٹہ", "zh": "按小时", "de": "Stundenweise", "it": "A ore",
  "ru": "Почасовая", "tr": "Saatlik", "ko": "시간제", "ja": "時間貸し",
  "vi": "Theo giờ", "fa": "ساعتی", "th": "รายชั่วโมง"
};

NOEL_I18N["form.flight_ph2"] = {
  "en": "e.g. EK215", "es": "p. ej., EK215", "fr": "p. ex. EK215", "ar": "مثال: EK215",
  "pt": "ex.: EK215", "ur": "masalan EK215", "hi": "जैसे EK215", "bn": "যেমন EK215",
  "ud": "جیسے EK215", "zh": "例如 EK215", "de": "z. B. EK215", "it": "es. EK215",
  "ru": "напр., EK215", "tr": "ör. EK215", "ko": "예: EK215", "ja": "例：EK215",
  "vi": "vd: EK215", "fa": "مثل EK215", "th": "เช่น EK215"
};

NOEL_I18N["status.plate_label"] = {
  "en": "Plate:", "es": "Matrícula:", "fr": "Plaque :", "ar": "اللوحة:",
  "pt": "Placa:", "ur": "Plate:", "hi": "प्लेट:", "bn": "প্লেট:",
  "ud": "پلیٹ:", "zh": "车牌：", "de": "Kennzeichen:", "it": "Targa:",
  "ru": "Номерной знак:", "tr": "Plaka:", "ko": "번호판:", "ja": "ナンバープレート：",
  "vi": "Biển số:", "fa": "پلاک:", "th": "ทะเบียนรถ:"
};

NOEL_I18N["class.prev_highlight"] = {
  "en": "Previous highlight", "es": "Aspecto anterior", "fr": "Point fort précédent", "ar": "الميزة السابقة",
  "pt": "Destaque anterior", "ur": "Pichli highlight", "hi": "पिछली विशेषता", "bn": "আগের হাইলাইট",
  "ud": "پچھلی نمایاں بات", "zh": "上一个亮点", "de": "Vorheriges Highlight", "it": "Evidenza precedente",
  "ru": "Предыдущее преимущество", "tr": "Önceki öne çıkan", "ko": "이전 특징", "ja": "前のハイライト",
  "vi": "Điểm nổi bật trước", "fa": "ویژگی قبلی", "th": "จุดเด่นก่อนหน้า"
};

NOEL_I18N["class.next_highlight"] = {
  "en": "Next highlight", "es": "Siguiente aspecto", "fr": "Point fort suivant", "ar": "الميزة التالية",
  "pt": "Próximo destaque", "ur": "Agli highlight", "hi": "अगली विशेषता", "bn": "পরের হাইলাইট",
  "ud": "اگلی نمایاں بات", "zh": "下一个亮点", "de": "Nächstes Highlight", "it": "Evidenza successiva",
  "ru": "Следующее преимущество", "tr": "Sonraki öne çıkan", "ko": "다음 특징", "ja": "次のハイライト",
  "vi": "Điểm nổi bật tiếp theo", "fa": "ویژگی بعدی", "th": "จุดเด่นถัดไป"
};

NOEL_I18N["class.highlights"] = {
  "en": "Highlights", "es": "Aspectos destacados", "fr": "Points forts", "ar": "المزايا",
  "pt": "Destaques", "ur": "Highlights", "hi": "मुख्य बातें", "bn": "হাইলাইট",
  "ud": "نمایاں باتیں", "zh": "亮点", "de": "Highlights", "it": "In evidenza",
  "ru": "Преимущества", "tr": "Öne çıkanlar", "ko": "특징", "ja": "ハイライト",
  "vi": "Điểm nổi bật", "fa": "ویژگی‌ها", "th": "จุดเด่น"
};

NOEL_I18N["menu.app_link"] = {
  "en": "App", "es": "App", "fr": "Appli", "ar": "التطبيق",
  "pt": "App", "ur": "App", "hi": "ऐप", "bn": "অ্যাপ",
  "ud": "ایپ", "zh": "应用", "de": "App", "it": "App",
  "ru": "Приложение", "tr": "Uygulama", "ko": "앱", "ja": "アプリ",
  "vi": "Ứng dụng", "fa": "برنامه", "th": "แอป"
};

NOEL_I18N["menu.drive_with_us"] = {
  "en": "Drive with us", "es": "Conduce con nosotros", "fr": "Conduisez avec nous", "ar": "قُد معنا",
  "pt": "Dirija conosco", "ur": "Hamare saath drive karen", "hi": "हमारे साथ चलाएँ", "bn": "আমাদের সাথে ড্রাইভ করুন",
  "ud": "ہمارے ساتھ ڈرائیو کریں", "zh": "加入我们开车", "de": "Fahren Sie mit uns", "it": "Guida con noi",
  "ru": "Работайте с нами", "tr": "Bizimle sürün", "ko": "함께 운전하기", "ja": "私たちと一緒に運転する",
  "vi": "Lái xe cùng chúng tôi", "fa": "با ما رانندگی کنید", "th": "ขับรถกับเรา"
};

NOEL_I18N["app.book_ride"] = {
  "en": "Book your ride", "es": "Reserva tu viaje", "fr": "Réservez votre trajet", "ar": "احجز رحلتك",
  "pt": "Reserve sua viagem", "ur": "Apni ride book karen", "hi": "अपनी सवारी बुक करें", "bn": "আপনার রাইড বুক করুন",
  "ud": "اپنی سواری بک کریں", "zh": "预订您的行程", "de": "Buchen Sie Ihre Fahrt", "it": "Prenota la tua corsa",
  "ru": "Забронировать поездку", "tr": "Yolculuğunuzu rezerve edin", "ko": "이동 예약", "ja": "乗車を予約する",
  "vi": "Đặt chuyến đi của bạn", "fa": "سفر خود را رزرو کنید", "th": "จองการเดินทางของคุณ"
};

NOEL_I18N["app.home"] = {
  "en": "Home", "es": "Inicio", "fr": "Accueil", "ar": "الرئيسية",
  "pt": "Início", "ur": "Home", "hi": "होम", "bn": "হোম",
  "ud": "ہوم", "zh": "首页", "de": "Startseite", "it": "Home",
  "ru": "Главная", "tr": "Ana Sayfa", "ko": "홈", "ja": "ホーム",
  "vi": "Trang chủ", "fa": "خانه", "th": "หน้าแรก"
};

NOEL_I18N["app.history_intro_past"] = {
  "en": "Enter the phone number you booked with to see your past rides.", "es": "Escribe el número de teléfono con el que reservaste para ver tus viajes pasados.", "fr": "Saisissez le numéro de téléphone utilisé pour réserver afin de voir vos trajets passés.", "ar": "أدخل رقم الهاتف الذي حجزت به لترى رحلاتك السابقة.",
  "pt": "Informe o número de telefone usado na reserva para ver suas viagens anteriores.", "ur": "Apni pichli rides dekhne ke liye wo phone number likhen jis se book kiya tha.", "hi": "अपनी पिछली सवारियाँ देखने के लिए वह फ़ोन नंबर लिखें जिससे आपने बुक किया था।", "bn": "আপনার আগের রাইড দেখতে যে ফোন নম্বর দিয়ে বুক করেছিলেন তা লিখুন।",
  "ud": "اپنی پچھلی سواریاں دیکھنے کے لیے وہ فون نمبر درج کریں جو آپ نے بکنگ کے لیے استعمال کیا تھا", "zh": "输入您预订时使用的电话号码以查看您过去的行程。", "de": "Geben Sie die Telefonnummer ein, mit der Sie gebucht haben, um Ihre vergangenen Fahrten zu sehen.", "it": "Inserisci il numero di telefono usato per la prenotazione per vedere le tue corse passate.",
  "ru": "Введите номер телефона, с которым вы бронировали, чтобы увидеть свои прошлые поездки.", "tr": "Geçmiş yolculuklarınızı görmek için rezervasyon yaptığınız telefon numarasını girin.", "ko": "예약 시 사용한 전화번호를 입력하면 지난 이동 내역을 볼 수 있습니다.", "ja": "予約時に使用した電話番号を入力すると、過去の乗車履歴が表示されます。",
  "vi": "Nhập số điện thoại bạn đã dùng để đặt xe để xem các chuyến đi trước đây của bạn.", "fa": "برای مشاهدهٔ سفرهای گذشتهٔ خود، شماره تلفنی را که برای رزرو استفاده کرده‌اید وارد کنید", "th": "ป้อนหมายเลขโทรศัพท์ที่คุณใช้จองเพื่อดูการเดินทางที่ผ่านมาของคุณ"
};

NOEL_I18N["status.looking_up"] = {
  "en": "Looking up your rides…", "es": "Buscando tus viajes…", "fr": "Recherche de vos trajets…", "ar": "جارٍ البحث عن رحلاتك…",
  "pt": "Procurando suas viagens…", "ur": "Aapki rides dhoondhi ja rahi hain…", "hi": "आपकी सवारियाँ खोजी जा रही हैं…", "bn": "আপনার রাইড খোঁজা হচ্ছে…",
  "ud": "آپ کی سواری تلاش کی جا رہی ہے…", "zh": "正在查找您的行程…", "de": "Ihre Fahrten werden gesucht…", "it": "Ricerca delle tue corse…",
  "ru": "Поиск ваших поездок…", "tr": "Yolculuklarınız aranıyor…", "ko": "이동을 조회하는 중…", "ja": "乗車を検索中…",
  "vi": "Đang tra cứu chuyến đi của bạn…", "fa": "در حال جستجوی سفر شما…", "th": "กำลังค้นหาการเดินทางของคุณ…"
};

NOEL_I18N["status.no_rides_email"] = {
  "en": "No rides found for this email yet.", "es": "Aún no hay viajes para este correo.", "fr": "Aucun trajet trouvé pour cet e-mail pour le moment.", "ar": "لم يتم العثور على رحلات لهذا البريد الإلكتروني بعد.",
  "pt": "Nenhuma viagem encontrada para este e-mail ainda.", "ur": "Is email ke liye abhi koi rides nahi mili.", "hi": "इस ईमेल के लिए अभी कोई सवारी नहीं मिली।", "bn": "এই ইমেইলের জন্য এখনো কোনো রাইড পাওয়া যায়নি।",
  "ud": "اس ای میل کے لیے ابھی کوئی سواری نہیں ملی", "zh": "未找到该邮箱的任何行程。", "de": "Für diese E-Mail-Adresse wurden noch keine Fahrten gefunden.", "it": "Ancora nessuna corsa trovata per questa email.",
  "ru": "По этой электронной почте пока не найдено поездок.", "tr": "Bu e-posta için henüz yolculuk bulunamadı.", "ko": "해당 이메일로 찾은 이동이 아직 없습니다.", "ja": "このメールではまだ乗車が見つかりません。",
  "vi": "Chưa tìm thấy chuyến đi nào cho email này.", "fa": "برای این ایمیل هنوز سفری یافت نشد", "th": "ยังไม่พบการเดินทางสำหรับอีเมลนี้"
};

NOEL_I18N["status.no_rides_number"] = {
  "en": "No rides found for that number yet.", "es": "Aún no hay viajes para ese número.", "fr": "Aucun trajet trouvé pour ce numéro pour le moment.", "ar": "لم يتم العثور على رحلات لهذا الرقم بعد.",
  "pt": "Nenhuma viagem encontrada para esse número ainda.", "ur": "Is number ke liye abhi koi rides nahi mili.", "hi": "इस नंबर के लिए अभी कोई सवारी नहीं मिली।", "bn": "এই নম্বরের জন্য এখনো কোনো রাইড পাওয়া যায়নি।",
  "ud": "اس نمبر کے لیے ابھی کوئی سواری نہیں ملی", "zh": "未找到该号码的任何行程。", "de": "Für diese Nummer wurden noch keine Fahrten gefunden.", "it": "Ancora nessuna corsa trovata per quel numero.",
  "ru": "По этому номеру пока не найдено поездок.", "tr": "Bu numara için henüz yolculuk bulunamadı.", "ko": "해당 번호로 찾은 이동이 아직 없습니다.", "ja": "この番号ではまだ乗車が見つかりません。",
  "vi": "Chưa tìm thấy chuyến đi nào cho số đó.", "fa": "برای آن شماره هنوز سفری یافت نشد", "th": "ยังไม่พบการเดินทางสำหรับหมายเลขนั้น"
};

NOEL_I18N["status.enter_phone"] = {
  "en": "Please enter your phone number.", "es": "Escribe tu número de teléfono.", "fr": "Veuillez saisir votre numéro de téléphone.", "ar": "يرجى إدخال رقم هاتفك.",
  "pt": "Informe seu número de telefone.", "ur": "Apna phone number likhen.", "hi": "कृपया अपना फ़ोन नंबर लिखें।", "bn": "আপনার ফোন নম্বর লিখুন।",
  "ud": "براہ کرم اپنا فون نمبر درج کریں", "zh": "请输入您的电话号码。", "de": "Bitte geben Sie Ihre Telefonnummer ein.", "it": "Inserisci il tuo numero di telefono.",
  "ru": "Пожалуйста, введите ваш номер телефона.", "tr": "Lütfen telefon numaranızı girin.", "ko": "전화번호를 입력해 주세요.", "ja": "電話番号を入力してください。",
  "vi": "Vui lòng nhập số điện thoại của bạn.", "fa": "لطفاً شماره تلفن خود را وارد کنید", "th": "โปรดป้อนหมายเลขโทรศัพท์ของคุณ"
};

NOEL_I18N["status.lookup_failed"] = {
  "en": "Could not look up rides for that number.", "es": "No se pudieron buscar viajes para ese número.", "fr": "Impossible de rechercher des trajets pour ce numéro.", "ar": "تعذّر البحث عن رحلات لهذا الرقم.",
  "pt": "Não foi possível buscar viagens para esse número.", "ur": "Is number ke liye rides nahi mil saki.", "hi": "उस नंबर के लिए सवारियाँ नहीं मिल सकीं।", "bn": "ওই নম্বরের জন্য রাইড খুঁজে পাওয়া যায়নি।",
  "ud": "اس نمبر کے لیے کوئی سواری نہیں ملی", "zh": "无法查找该号码的行程。", "de": "Fahrten für diese Nummer konnten nicht gesucht werden.", "it": "Non è stato possibile cercare le corse per quel numero.",
  "ru": "Не удалось найти поездки для этого номера.", "tr": "Bu numara için yolculuk bulunamadı.", "ko": "해당 번호의 이동을 찾을 수 없습니다.", "ja": "その番号の乗車を検索できませんでした。",
  "vi": "Không thể tra cứu chuyến đi cho số đó.", "fa": "برای آن شماره سفری یافت نشد", "th": "ไม่สามารถค้นหาการเดินทางสำหรับหมายเลขนั้นได้"
};

NOEL_I18N["app.my_rides"] = {
  "en": "My Rides", "es": "Mis viajes", "fr": "Mes trajets", "ar": "رحلاتي",
  "pt": "Minhas viagens", "ur": "Meri Rides", "hi": "मेरी सवारियाँ", "bn": "আমার রাইডগুলো",
  "ud": "میری سواریاں", "zh": "我的行程", "de": "Meine Fahrten", "it": "Le mie corse",
  "ru": "Мои поездки", "tr": "Yolculuklarım", "ko": "내 이동", "ja": "マイ乗車",
  "vi": "Chuyến đi của tôi", "fa": "سفرهای من", "th": "การเดินทางของฉัน"
};

NOEL_I18N["app.support"] = {
  "en": "Support", "es": "Ayuda", "fr": "Assistance", "ar": "الدعم",
  "pt": "Suporte", "ur": "Support", "hi": "सहायता", "bn": "সহায়তা",
  "ud": "سپورٹ", "zh": "客服支持", "de": "Support", "it": "Assistenza",
  "ru": "Поддержка", "tr": "Destek", "ko": "고객 지원", "ja": "サポート",
  "vi": "Hỗ trợ", "fa": "پشتیبانی", "th": "ฝ่ายสนับสนุน"
};

NOEL_I18N["app.book_your_ride"] = {
  "en": "Book your ride", "es": "Reserva tu viaje", "fr": "Réservez votre trajet", "ar": "احجز رحلتك",
  "pt": "Reserve sua viagem", "ur": "Apni ride book karen", "hi": "अपनी सवारी बुक करें", "bn": "আপনার রাইড বুক করুন",
  "ud": "اپنی سواری بک کریں", "zh": "预订您的行程", "de": "Buchen Sie Ihre Fahrt", "it": "Prenota la tua corsa",
  "ru": "Забронировать поездку", "tr": "Yolculuğunuzu rezerve edin", "ko": "이동 예약", "ja": "乗車を予約する",
  "vi": "Đặt chuyến đi của bạn", "fa": "سفر خود را رزرو کنید", "th": "จองการเดินทางของคุณ"
};

NOEL_I18N["app.your_rides"] = {
  "en": "Your rides", "es": "Tus viajes", "fr": "Vos trajets", "ar": "رحلاتك",
  "pt": "Suas viagens", "ur": "Aapki rides", "hi": "आपकी सवारियाँ", "bn": "আপনার রাইডগুলো",
  "ud": "آپ کی سواریاں", "zh": "您的行程", "de": "Ihre Fahrten", "it": "Le tue corse",
  "ru": "Ваши поездки", "tr": "Yolculuklarınız", "ko": "고객님의 이동", "ja": "お客様の乗車",
  "vi": "Chuyến đi của bạn", "fa": "سفرهای شما", "th": "การเดินทางของคุณ"
};

NOEL_I18N["app.book_another"] = {
  "en": "Book another ride", "es": "Reservar otro viaje", "fr": "Réserver un autre trajet", "ar": "احجز رحلة أخرى",
  "pt": "Reservar outra viagem", "ur": "Ek aur ride book karen", "hi": "एक और सवारी बुक करें", "bn": "আরেকটি রাইড বুক করুন",
  "ud": "دوسری سواری بک کریں", "zh": "再预订一次行程", "de": "Eine weitere Fahrt buchen", "it": "Prenota un'altra corsa",
  "ru": "Забронировать ещё одну поездку", "tr": "Başka bir yolculuk rezervasyonu yap", "ko": "다른 이동 예약", "ja": "別の乗車を予約する",
  "vi": "Đặt một chuyến đi khác", "fa": "یک سفر دیگر رزرو کنید", "th": "จองการเดินทางอื่น"
};

NOEL_I18N["app.book_return"] = {
  "en": "Book your return trip", "es": "Reserva tu viaje de regreso", "fr": "Réservez votre trajet retour", "ar": "احجز رحلة عودتك",
  "pt": "Reserve sua viagem de volta", "ur": "Apni return trip book karen", "hi": "अपनी वापसी यात्रा बुक करें", "bn": "আপনার ফেরার যাত্রা বুক করুন",
  "ud": "اپنی واپسی کی سواری بک کریں", "zh": "预订您的返程", "de": "Buchen Sie Ihre Rückfahrt", "it": "Prenota il viaggio di ritorno",
  "ru": "Забронировать обратную поездку", "tr": "Dönüş yolculuğunuzu rezerve edin", "ko": "귀환 여정 예약", "ja": "帰りの乗車を予約する",
  "vi": "Đặt chuyến về của bạn", "fa": "سفر برگشت خود را رزرو کنید", "th": "จองเที่ยวกลับของคุณ"
};

NOEL_I18N["app.support_heading"] = {
  "en": "How can we help?", "es": "¿Cómo podemos ayudarte?", "fr": "Comment pouvons-nous vous aider ?", "ar": "كيف يمكننا مساعدتك؟",
  "pt": "Como podemos ajudar?", "ur": "Hum kaise madad kar sakte hain?", "hi": "हम कैसे मदद कर सकते हैं?", "bn": "আমরা কীভাবে সাহায্য করতে পারি?",
  "ud": "ہم کس طرح مدد کر سکتے ہیں؟", "zh": "我们能帮您什么？", "de": "Wie können wir helfen?", "it": "Come possiamo aiutarti?",
  "ru": "Чем мы можем помочь?", "tr": "Nasıl yardımcı olabiliriz?", "ko": "어떻게 도와드릴까요?", "ja": "どのようなご用件でしょうか？",
  "vi": "Chúng tôi có thể giúp gì?", "fa": "چگونه می‌توانیم کمک کنیم؟", "th": "เราช่วยอะไรได้บ้าง?"
};

NOEL_I18N["app.support_text"] = {
  "en": "Email us at info@noelchauffer.com or send us a message below.", "es": "Escríbenos a info@noelchauffer.com o envíanos un mensaje abajo.", "fr": "Écrivez-nous à info@noelchauffer.com ou envoyez-nous un message ci-dessous.", "ar": "راسلنا على info@noelchauffer.com أو أرسل لنا رسالة أدناه.",
  "pt": "Envie um e-mail para info@noelchauffer.com ou envie-nos uma mensagem abaixo.", "ur": "Hamein info@noelchauffer.com par email karen ya neeche message bhejen.", "hi": "हमें info@noelchauffer.com पर ईमेल करें या नीचे संदेश भेजें।", "bn": "info@noelchauffer.com-এ ইমেইল করুন বা নিচে বার্তা পাঠান।",
  "ud": "ہمیں info@noelchauffer.com پر ای میل کریں یا نیچے پیغام بھیجیں", "zh": "请发送邮件至 info@noelchauffer.com，或在下方留言。", "de": "Schreiben Sie uns an info@noelchauffer.com oder senden Sie uns unten eine Nachricht.", "it": "Scrivici a info@noelchauffer.com o inviaci un messaggio qui sotto.",
  "ru": "Напишите нам на info@noelchauffer.com или отправьте сообщение ниже.", "tr": "Bize info@noelchauffer.com adresine e-posta gönderin veya aşağıya bir mesaj yazın.", "ko": "info@noelchauffer.com으로 이메일을 보내시거나 아래에 메시지를 남겨주세요.", "ja": "info@noelchauffer.comまでメールをお送りいただくか、以下にメッセージをお送りください。",
  "vi": "Gửi email cho chúng tôi tại info@noelchauffer.com hoặc gửi tin nhắn bên dưới.", "fa": "به ما در info@noelchauffer.com ایمیل بزنید یا در زیر پیام بفرستید", "th": "ส่งอีเมลหาเราที่ info@noelchauffer.com หรือส่งข้อความด้านล่าง"
};

NOEL_I18N["app.chat_placeholder"] = {
  "en": "Type a message…", "es": "Escribe un mensaje…", "fr": "Écrivez un message…", "ar": "اكتب رسالة…",
  "pt": "Digite uma mensagem…", "ur": "Message likhen…", "hi": "संदेश लिखें…", "bn": "বার্তা লিখুন…",
  "ud": "پیغام لکھیں…", "zh": "输入消息…", "de": "Nachricht eingeben…", "it": "Scrivi un messaggio…",
  "ru": "Введите сообщение…", "tr": "Bir mesaj yazın…", "ko": "메시지 입력…", "ja": "メッセージを入力…",
  "vi": "Nhập tin nhắn…", "fa": "پیام بنویسید…", "th": "พิมพ์ข้อความ…"
};

NOEL_I18N["app.send"] = {
  "en": "Send", "es": "Enviar", "fr": "Envoyer", "ar": "إرسال",
  "pt": "Enviar", "ur": "Send", "hi": "भेजें", "bn": "পাঠান",
  "ud": "بھیجیں", "zh": "发送", "de": "Senden", "it": "Invia",
  "ru": "Отправить", "tr": "Gönder", "ko": "보내기", "ja": "送信",
  "vi": "Gửi", "fa": "ارسال", "th": "ส่ง"
};

NOEL_I18N["app.chat_language"] = {
  "en": "Chat language", "es": "Idioma del chat", "fr": "Langue du chat", "ar": "لغة المحادثة",
  "pt": "Idioma do chat", "ur": "Chat ki language", "hi": "चैट की भाषा", "bn": "চ্যাটের ভাষা",
  "ud": "چیٹ کی زبان", "zh": "聊天语言", "de": "Chat-Sprache", "it": "Lingua della chat",
  "ru": "Язык чата", "tr": "Sohbet dili", "ko": "채팅 언어", "ja": "チャット言語",
  "vi": "Ngôn ngữ trò chuyện", "fa": "زبان چت", "th": "ภาษาแชท"
};

NOEL_I18N["app.no_rides"] = {
  "en": "No rides yet.", "es": "Aún no hay viajes.", "fr": "Aucun trajet pour le moment.", "ar": "لا توجد رحلات بعد.",
  "pt": "Nenhuma viagem ainda.", "ur": "Abhi koi rides nahi hain.", "hi": "अभी कोई सवारी नहीं है।", "bn": "এখনো কোনো রাইড নেই।",
  "ud": "ابھی کوئی سواری نہیں", "zh": "暂无行程。", "de": "Noch keine Fahrten.", "it": "Ancora nessuna corsa.",
  "ru": "Пока нет поездок.", "tr": "Henüz yolculuk yok.", "ko": "아직 이동이 없습니다.", "ja": "まだ乗車がありません。",
  "vi": "Chưa có chuyến đi nào.", "fa": "هنوز سفری نیست", "th": "ยังไม่มีการเดินทาง"
};

NOEL_I18N["app.finding_driver"] = {
  "en": "Finding your chauffeur", "es": "Buscando tu chófer", "fr": "Recherche de votre chauffeur", "ar": "جارٍ البحث عن سائقك",
  "pt": "Procurando seu motorista", "ur": "Aapka chauffeur dhoondha ja raha hai", "hi": "आपका शॉफ़र खोजा जा रहा है", "bn": "আপনার শোফার খোঁজা হচ্ছে",
  "ud": "آپ کے لیے ڈرائیور تلاش کیا جا رہا ہے", "zh": "正在为您寻找司机", "de": "Ihr Chauffeur wird gesucht", "it": "Ricerca del tuo chauffeur",
  "ru": "Поиск вашего шофёра", "tr": "Şoförünüz aranıyor", "ko": "쇼퍼를 찾고 있습니다", "ja": "ショファーを探しています",
  "vi": "Đang tìm tài xế cho bạn", "fa": "در حال یافتن راننده برای شما", "th": "กำลังหาคนขับให้คุณ"
};

NOEL_I18N["app.your_chauffeur"] = {
  "en": "Your chauffeur", "es": "Tu chófer", "fr": "Votre chauffeur", "ar": "سائقك",
  "pt": "Seu motorista", "ur": "Aapka chauffeur", "hi": "आपका शॉफ़र", "bn": "আপনার শোফার",
  "ud": "آپ کا ڈرائیور", "zh": "您的司机", "de": "Ihr Chauffeur", "it": "Il tuo chauffeur",
  "ru": "Ваш шофёр", "tr": "Şoförünüz", "ko": "고객님의 쇼퍼", "ja": "お客様のショファー",
  "vi": "Tài xế của bạn", "fa": "رانندهٔ شما", "th": "คนขับของคุณ"
};

NOEL_I18N["app.live_map"] = {
  "en": "Live map", "es": "Mapa en vivo", "fr": "Carte en direct", "ar": "الخريطة المباشرة",
  "pt": "Mapa ao vivo", "ur": "Live map", "hi": "लाइव मैप", "bn": "লাইভ মানচিত্র",
  "ud": "لائیو نقشہ", "zh": "实时地图", "de": "Live-Karte", "it": "Mappa live",
  "ru": "Карта в реальном времени", "tr": "Canlı harita", "ko": "실시간 지도", "ja": "ライブマップ",
  "vi": "Bản đồ trực tiếp", "fa": "نقشهٔ زنده", "th": "แผนที่สด"
};

NOEL_I18N["app.arrives"] = {
  "en": "arrives", "es": "llega", "fr": "arrive", "ar": "يصل",
  "pt": "chega", "ur": "aata hai", "hi": "पहुँचता है", "bn": "আসছে",
  "ud": "پہنچتا ہے", "zh": "到达", "de": "kommt an", "it": "arriva",
  "ru": "прибывает", "tr": "varıyor", "ko": "도착", "ja": "到着",
  "vi": "đến", "fa": "می‌رسد", "th": "ถึง"
};

NOEL_I18N["app.driver_heading"] = {
  "en": "Driver is heading to you", "es": "El chófer viene hacia ti", "fr": "Le chauffeur vient vers vous", "ar": "السائق في طريقه إليك",
  "pt": "O motorista está indo até você", "ur": "Driver aapki taraf aa raha hai", "hi": "ड्राइवर आपकी ओर आ रहा है", "bn": "ড্রাইভার আপনার দিকে আসছেন",
  "ud": "آپ کا ڈرائیور آپ کی طرف آ رہا ہے", "zh": "司机正在前往您处", "de": "Der Fahrer ist auf dem Weg zu Ihnen", "it": "L'autista sta arrivando da te",
  "ru": "Водитель едет к вам", "tr": "Sürücü size doğru geliyor", "ko": "기사가 고객님께 오고 있습니다", "ja": "ドライバーがお客様のもとへ向かっています",
  "vi": "Tài xế đang đến chỗ bạn", "fa": "رانندهٔ شما در راه است", "th": "คนขับกำลังมุ่งหน้าไปหาคุณ"
};

NOEL_I18N["app.cancelled"] = {
  "en": "Cancelled", "es": "Cancelado", "fr": "Annulé", "ar": "ملغاة",
  "pt": "Cancelado", "ur": "Cancel", "hi": "रद्द", "bn": "বাতিল",
  "ud": "منسوخ شدہ", "zh": "已取消", "de": "Storniert", "it": "Annullata",
  "ru": "Отменено", "tr": "İptal edildi", "ko": "취소됨", "ja": "キャンセル済み",
  "vi": "Đã hủy", "fa": "لغوشده", "th": "ยกเลิกแล้ว"
};

NOEL_I18N["app.completed"] = {
  "en": "Completed", "es": "Completado", "fr": "Terminé", "ar": "مكتملة",
  "pt": "Concluído", "ur": "Completed", "hi": "पूर्ण", "bn": "সম্পূর্ণ",
  "ud": "مکمل شدہ", "zh": "已完成", "de": "Abgeschlossen", "it": "Completata",
  "ru": "Завершено", "tr": "Tamamlandı", "ko": "완료됨", "ja": "完了",
  "vi": "Đã hoàn thành", "fa": "تکمیل‌شده", "th": "เสร็จสิ้น"
};

NOEL_I18N["app.sign_in"] = {
  "en": "Sign in", "es": "Iniciar sesión", "fr": "Se connecter", "ar": "تسجيل الدخول",
  "pt": "Entrar", "ur": "Sign in", "hi": "साइन इन करें", "bn": "সাইন ইন করুন",
  "ud": "سائن ان کریں", "zh": "登录", "de": "Anmelden", "it": "Accedi",
  "ru": "Войти", "tr": "Giriş yap", "ko": "로그인", "ja": "サインイン",
  "vi": "Đăng nhập", "fa": "ورود", "th": "เข้าสู่ระบบ"
};

NOEL_I18N["app.language"] = {
  "en": "Language", "es": "Idioma", "fr": "Langue", "ar": "اللغة",
  "pt": "Idioma", "ur": "Language", "hi": "भाषा", "bn": "ভাষা",
  "ud": "زبان", "zh": "语言", "de": "Sprache", "it": "Lingua",
  "ru": "Язык", "tr": "Dil", "ko": "언어", "ja": "言語",
  "vi": "Ngôn ngữ", "fa": "زبان", "th": "ภาษา"
};

NOEL_I18N["lang.no_results"] = {
  "en": "No language found", "es": "No se encontró ningún idioma", "fr": "Aucune langue trouvée", "ar": "لم يتم العثور على لغة",
  "pt": "Nenhum idioma encontrado", "ur": "Koi language nahi mili", "hi": "कोई भाषा नहीं मिली", "bn": "কোনো ভাষা পাওয়া যায়নি",
  "ud": "کوئی زبان نہیں ملی", "zh": "未找到语言", "de": "Keine Sprache gefunden", "it": "Nessuna lingua trovata",
  "ru": "Язык не найден", "tr": "Dil bulunamadı", "ko": "언어를 찾을 수 없습니다", "ja": "言語が見つかりません",
  "vi": "Không tìm thấy ngôn ngữ", "fa": "زبانی یافت نشد", "th": "ไม่พบภาษา"
};

NOEL_I18N["app.search_language"] = {
  "en": "Search language…", "es": "Buscar idioma…", "fr": "Rechercher une langue…", "ar": "ابحث عن لغة…",
  "pt": "Buscar idioma…", "ur": "Language search karen…", "hi": "भाषा खोजें…", "bn": "ভাষা খুঁজুন…",
  "ud": "زبان تلاش کریں…", "zh": "搜索语言…", "de": "Sprache suchen…", "it": "Cerca lingua…",
  "ru": "Поиск языка…", "tr": "Dil ara…", "ko": "언어 검색…", "ja": "言語を検索…",
  "vi": "Tìm ngôn ngữ…", "fa": "جستجوی زبان…", "th": "ค้นหาภาษา…"
};

NOEL_I18N["chat.reply_24"] = {
  "en": "We reply within 24 hours.", "es": "Respondemos en un plazo de 24 horas.", "fr": "Nous répondons sous 24 heures.", "ar": "نرد خلال 24 ساعة.",
  "pt": "Respondemos em até 24 horas.", "ur": "Hum 24 hours ke andar reply karte hain.", "hi": "हम 24 घंटों के भीतर जवाब देते हैं।", "bn": "আমরা ২৪ ঘণ্টার মধ্যে উত্তর দিই।",
  "ud": "ہم 24 گھنٹوں کے اندر جواب دیتے ہیں", "zh": "我们在24小时内回复。", "de": "Wir antworten innerhalb von 24 Stunden.", "it": "Rispondiamo entro 24 ore.",
  "ru": "Мы отвечаем в течение 24 часов.", "tr": "24 saat içinde yanıt veriyoruz.", "ko": "24시간 이내에 답변합니다.", "ja": "24時間以内に返信します。",
  "vi": "Chúng tôi trả lời trong vòng 24 giờ.", "fa": "ما ظرف ۲۴ ساعت پاسخ می‌دهیم", "th": "เราตอบกลับภายใน 24 ชั่วโมง"
};

NOEL_I18N["chat.chip_book"] = {
  "en": "How do I book?", "es": "¿Cómo reservo?", "fr": "Comment réserver ?", "ar": "كيف أحجز؟",
  "pt": "Como reservo?", "ur": "Book kaise karen?", "hi": "बुक कैसे करें?", "bn": "কীভাবে বুক করব?",
  "ud": "کیسے بک کریں؟", "zh": "如何预订？", "de": "Wie buche ich?", "it": "Come prenoto?",
  "ru": "Как забронировать?", "tr": "Nasıl rezervasyon yaparım?", "ko": "예약은 어떻게 하나요?", "ja": "予約方法は？",
  "vi": "Tôi đặt xe như thế nào?", "fa": "چگونه رزرو کنم؟", "th": "จองอย่างไร?"
};

NOEL_I18N["chat.chip_paused"] = {
  "en": "Are bookings paused?", "es": "¿Están en pausa las reservas?", "fr": "Les réservations sont-elles suspendues ?", "ar": "هل الحجوزات متوقفة؟",
  "pt": "As reservas estão pausadas?", "ur": "Kya bookings paused hain?", "hi": "क्या बुकिंग रुकी हुई हैं?", "bn": "বুকিং কি থেমে আছে?",
  "ud": "کیا بکنگ رکی ہوئی ہے؟", "zh": "预订暂停了吗？", "de": "Sind Buchungen pausiert?", "it": "Le prenotazioni sono in pausa?",
  "ru": "Бронирование приостановлено?", "tr": "Rezervasyonlar duraklatıldı mı?", "ko": "예약이 중단되었나요?", "ja": "予約は一時停止中ですか？",
  "vi": "Đặt xe có bị tạm dừng không?", "fa": "آیا رزرو متوقف شده است؟", "th": "การจองหยุดชั่วคราวหรือไม่?"
};

NOEL_I18N["chat.chip_cancel"] = {
  "en": "Cancellation rules", "es": "Reglas de cancelación", "fr": "Règles d'annulation", "ar": "قواعد الإلغاء",
  "pt": "Regras de cancelamento", "ur": "Cancellation rules", "hi": "रद्द करने के नियम", "bn": "বাতিলের নিয়ম",
  "ud": "منسوخی کے اصول", "zh": "取消规则", "de": "Stornierungsbedingungen", "it": "Regole di cancellazione",
  "ru": "Правила отмены", "tr": "İptal kuralları", "ko": "취소 규정", "ja": "キャンセル規定",
  "vi": "Quy định hủy xe", "fa": "قوانین لغو", "th": "กฎการยกเลิก"
};

NOEL_I18N["chat.chip_waiting"] = {
  "en": "Waiting time", "es": "Tiempo de espera", "fr": "Temps d'attente", "ar": "وقت الانتظار",
  "pt": "Tempo de espera", "ur": "Waiting time", "hi": "प्रतीक्षा समय", "bn": "অপেক্ষার সময়",
  "ud": "انتظار کا وقت", "zh": "等候时间", "de": "Wartezeit", "it": "Tempo di attesa",
  "ru": "Время ожидания", "tr": "Bekleme süresi", "ko": "대기 시간", "ja": "待ち時間",
  "vi": "Thời gian chờ", "fa": "زمان انتظار", "th": "เวลารอ"
};

NOEL_I18N["chat.chip_lost"] = {
  "en": "Lost item", "es": "Objeto perdido", "fr": "Objet perdu", "ar": "غرض مفقود",
  "pt": "Objeto perdido", "ur": "Lost item", "hi": "खोया सामान", "bn": "হারানো জিনিস",
  "ud": "گمشدہ چیز", "zh": "遗失物品", "de": "Verlorener Gegenstand", "it": "Oggetto smarrito",
  "ru": "Потерянная вещь", "tr": "Kayıp eşya", "ko": "분실물", "ja": "紛失物",
  "vi": "Đồ thất lạc", "fa": "وسیلهٔ گمشده", "th": "ของหาย"
};

NOEL_I18N["chat.title"] = {
  "en": "Chat with us", "es": "Chatea con nosotros", "fr": "Discutez avec nous", "ar": "تحدث معنا",
  "pt": "Fale conosco", "ur": "Hum se chat karen", "hi": "हमसे चैट करें", "bn": "আমাদের সঙ্গে চ্যাট করুন",
  "ud": "ہم سے چیٹ کریں", "zh": "与我们聊天", "de": "Chat mit uns", "it": "Chatta con noi",
  "ru": "Чат с нами", "tr": "Bize yazın", "ko": "문의 채팅", "ja": "チャットする",
  "vi": "Trò chuyện với chúng tôi", "fa": "با ما چت کنید", "th": "แชทกับเรา"
};

NOEL_I18N["chat.greeting_app"] = {
  "en": "Hello, and welcome to Noel Chauffer. How can I help — booking, cancellation, waiting time, or something about a ride?", "es": "Hola, bienvenido a Noel Chauffer. ¿Cómo puedo ayudarte: reserva, cancelación, tiempo de espera o algo sobre un viaje?", "fr": "Bonjour et bienvenue chez Noel Chauffer. Comment puis-je vous aider — réservation, annulation, temps d'attente ou autre chose sur un trajet ?", "ar": "مرحبًا بك في نويل شوفير. كيف يمكنني مساعدتك — الحجز أو الإلغاء أو وقت الانتظار أو شيء عن رحلة؟",
  "pt": "Olá, bem-vindo à Noel Chauffer. Como posso ajudar — reserva, cancelamento, tempo de espera ou algo sobre uma viagem?", "ur": "Hello, Noel Chauffer mein welcome. Main kaise madad kar sakta hoon — booking, cancellation, waiting time, ya ride ke baare mein kuch?", "hi": "नमस्ते, नोएल शॉफ़र में स्वागत है। मैं कैसे मदद कर सकता हूँ — बुकिंग, रद्दीकरण, प्रतीक्षा समय, या सवारी के बारे में कुछ?", "bn": "হ্যালো, নোয়েল শোফারে স্বাগতম। আমি কীভাবে সাহায্য করতে পারি — বুকিং, বাতিল, অপেক্ষার সময়, বা রাইড সম্পর্কে কিছু?",
  "ud": "ہیلو، Noel Chauffer میں خوش آمدید۔ میں کس طرح مدد کر سکتا ہوں — بکنگ، منسوخی، انتظار کا وقت، یا سواری کے بارے میں کچھ؟", "zh": "您好，欢迎来到 Noel Chauffer。我能帮您什么——预订、取消、等候时间或关于行程的事？", "de": "Hallo und willkommen bei Noel Chauffer. Wie kann ich helfen — Buchung, Stornierung, Wartezeit oder etwas zu einer Fahrt?", "it": "Ciao e benvenuto da Noel Chauffer. Come posso aiutarti — prenotazione, cancellazione, tempo di attesa o qualcosa su una corsa?",
  "ru": "Здравствуйте, добро пожаловать в Noel Chauffer. Чем я могу помочь — бронирование, отмена, время ожидания или что-то о поездке?", "tr": "Merhaba, Noel Chauffer'a hoş geldiniz. Nasıl yardımcı olabilirim — rezervasyon, iptal, bekleme süresi veya bir yolculuk hakkında bir şey mi?", "ko": "안녕하세요, Noel Chauffer에 오신 것을 환영합니다. 예약, 취소, 대기 시간 또는 이동에 대해 어떻게 도와드릴까요?", "ja": "こんにちは、Noel Chaufferへようこそ。予約、キャンセル、待ち時間、乗車についてどのようにお手伝いできますか？",
  "vi": "Xin chào, chào mừng bạn đến với Noel Chauffer. Tôi có thể giúp gì — đặt xe, hủy xe, thời gian chờ, hay điều gì về chuyến đi?", "fa": "سلام، به Noel Chauffer خوش آمدید. چگونه می‌توانم کمک کنم — رزرو، لغو، زمان انتظار یا چیزی دربارهٔ سفر؟", "th": "สวัสดี ยินดีต้อนรับสู่ Noel Chauffer ฉันช่วยอะไรได้บ้าง — การจอง การยกเลิก เวลารอ หรือเรื่องเกี่ยวกับการเดินทาง?"
};

NOEL_I18N["chat.ans_price_app"] = {
  "en": "Enter your pickup and drop-off in the Book tab, choose your experience, and you will see the total for each class before you pay.", "es": "Escribe tu recogida y destino en la pestaña Reservar, elige tu experiencia y verás el total de cada clase antes de pagar.", "fr": "Saisissez votre lieu de prise en charge et votre destination dans l'onglet Réserver, choisissez votre expérience et vous verrez le total de chaque classe avant de payer.", "ar": "أدخل مكان الاستلام والوصول في تبويب الحجز، واختر تجربتك، وسترى المجموع لكل فئة قبل الدفع.",
  "pt": "Informe embarque e destino na aba Reservar, escolha sua experiência e você verá o total de cada classe antes de pagar.", "ur": "Book tab mein apna pickup aur drop-off likhen, apna experience chunen, aur pay karne se pehle har class ka total dekh lenge.", "hi": "बुक टैब में अपना पिकअप और ड्रॉप-ऑफ़ लिखें, अपना अनुभव चुनें, और भुगतान से पहले आप हर श्रेणी का कुल देखेंगे।", "bn": "বুক ট্যাবে আপনার পিকআপ ও ড্রপ-অফ লিখুন, আপনার অভিজ্ঞতা বেছে নিন, এবং পেমেন্টের আগে প্রতিটি শ্রেণির মোট দেখতে পাবেন।",
  "ud": "بکنگ ٹیب میں پک اپ اور ڈراپ آف کے پتے درج کریں، اپنا تجربہ منتخب کریں، اور ادائیگی سے پہلے آپ کو ہر کلاس کی کل رقم نظر آ جائے گی", "zh": "请在“预订”选项卡中输入上车和下车地址，选择您的体验，付款前您将看到每个级别的总价。", "de": "Geben Sie Abhol- und Zielort im Tab „Buchen“ ein, wählen Sie Ihr Erlebnis und Sie sehen den Gesamtpreis für jede Klasse, bevor Sie bezahlen.", "it": "Inserisci il luogo di partenza e di destinazione nella scheda Prenota, scegli la tua esperienza e vedrai il totale per ogni classe prima di pagare.",
  "ru": "Введите адрес отправления и назначения во вкладке «Бронирование», выберите класс, и вы увидите общую стоимость для каждого класса перед оплатой.", "tr": "Biniş ve varış adresinizi Rezervasyon sekmesine girin, deneyiminizi seçin; ödemeden önce her sınıf için toplamı göreceksiniz.", "ko": "예약 탭에 출발지와 목적지를 입력하고 경험을 선택하면 결제 전에 각 클래스별 총액을 확인할 수 있습니다.", "ja": "「予約」タブに出発地と目的地を入力し、エクスペリエンスを選択すると、お支払い前に各クラスの合計が表示されます。",
  "vi": "Nhập địa chỉ đón và trả khách trong tab Đặt xe, chọn trải nghiệm của bạn và bạn sẽ thấy tổng giá cho mỗi hạng trước khi thanh toán.", "fa": "در زبانهٔ رزرو، نشانی‌های مبدا و مقصد را وارد کنید، تجربهٔ خود را انتخاب کنید و پیش از پرداخت، مجموع هر کلاس را خواهید دید", "th": "ป้อนที่อยู่ต้นทางและปลายทางในแท็บจอง เลือกประสบการณ์ของคุณ แล้วคุณจะเห็นยอดรวมของแต่ละระดับก่อนชำระเงิน"
};

NOEL_I18N["chat.ans_driver_app"] = {
  "en": "As soon as your chauffeur accepts, you will see their name, phone number, car, colour and plate number in the My Rides tab — and the same details are sent to your phone and email.", "es": "En cuanto tu chófer acepte, verás su nombre, número de teléfono, coche, color y matrícula en la pestaña Mis viajes, y los mismos datos se enviarán a tu teléfono y correo.", "fr": "Dès que votre chauffeur accepte, vous verrez son nom, son numéro de téléphone, sa voiture, sa couleur et sa plaque dans l'onglet Mes trajets — et ces mêmes informations seront envoyées sur votre téléphone et par e-mail.", "ar": "بمجرد أن يقبل سائقك، سترى اسمه ورقم هاتفه وسيارته ولونها ورقم لوحتها في تبويب رحلاتي — وستُرسل التفاصيل نفسها إلى هاتفك وبريدك الإلكتروني.",
  "pt": "Assim que seu motorista aceitar, você verá o nome, o telefone, o carro, a cor e a placa dele na aba Minhas viagens — e os mesmos dados serão enviados para seu telefone e e-mail.", "ur": "Jaise hi aapka chauffeur accept karega, aapko My Rides tab mein unka naam, phone number, gaadi, colour aur plate number dikhega — aur yehi details aapke phone aur email par bhi bheji jayengi.", "hi": "जैसे ही आपका शॉफ़र स्वीकार करेगा, आपको My Rides टैब में उनका नाम, फ़ोन नंबर, गाड़ी, रंग और नंबर प्लेट दिखेगा — और यही जानकारी आपके फ़ोन और ईमेल पर भी भेजी जाएगी।", "bn": "আপনার শোফার গ্রহণ করলেই My Rides ট্যাবে তাঁর নাম, ফোন নম্বর, গাড়ি, রং ও নম্বর প্লেট দেখতে পাবেন — আর একই বিবরণ আপনার ফোন ও ইমেইলে পাঠানো হবে।",
  "ud": "جیسے ہی آپ کا ڈرائیور قبول کرے گا، آپ کو میری سواریاں ٹیب میں اس کا نام، فون نمبر، گاڑی، رنگ اور پلیٹ نمبر نظر آئے گا — اور وہی تفصیلات آپ کے فون اور ای میل پر بھی بھیجی جائیں گی", "zh": "司机接受订单后，您将在“我的行程”选项卡中看到他的姓名、电话号码、车辆、颜色和车牌号——相同信息也会发送到您的手机和邮箱。", "de": "Sobald Ihr Chauffeur akzeptiert, sehen Sie seinen Namen, seine Telefonnummer, sein Auto, seine Farbe und sein Kennzeichen im Tab „Meine Fahrten“ — und dieselben Daten werden an Ihr Telefon und Ihre E-Mail-Adresse gesendet.", "it": "Non appena il tuo chauffeur accetta, vedrai il suo nome, numero di telefono, auto, colore e numero di targa nella scheda Le mie corse — e gli stessi dati verranno inviati al tuo telefono e alla tua email.",
  "ru": "Как только ваш шофёр примет заказ, вы увидите его имя, номер телефона, автомобиль, цвет и номерной знак во вкладке «Мои поездки» — и те же данные будут отправлены на ваш телефон и электронную почту.", "tr": "Şoförünüz kabul eder etmez adını, telefon numarasını, aracını, rengini ve plaka numarasını Yolculuklarım sekmesinde göreceksiniz — aynı bilgiler telefonunuza ve e-postanıza da gönderilir.", "ko": "쇼퍼가 수락하는 즉시 내 이동 탭에서 이름, 전화번호, 차량, 색상, 번호판을 확인할 수 있으며 같은 정보가 휴대폰과 이메일로도 전송됩니다.", "ja": "ショファーが承諾すると、「マイ乗車」タブに名前、電話番号、車、色、ナンバープレートが表示されます。同じ詳細がお客様の電話とメールにも送信されます。",
  "vi": "Ngay khi tài xế của bạn chấp nhận, bạn sẽ thấy tên, số điện thoại, xe, màu sắc và biển số của họ trong tab Chuyến đi của tôi — và các thông tin tương tự cũng được gửi đến điện thoại và email của bạn.", "fa": "به‌محض اینکه رانندهٔ شما قبول کند، نام، شماره تلفن، خودرو، رنگ و پلاک او را در زبانهٔ سفرهای من خواهید دید — و همان جزئیات به تلفن و ایمیل شما نیز ارسال می‌شود", "th": "ทันทีที่คนขับของคุณตอบรับ คุณจะเห็นชื่อ หมายเลขโทรศัพท์ รถยนต์ สี และหมายเลขทะเบียนในแท็บการเดินทางของฉัน — และรายละเอียดเดียวกันจะถูกส่งไปยังโทรศัพท์และอีเมลของคุณ"
};

NOEL_I18N["chat.ans_return_app"] = {
  "en": "For a return journey, simply book a second one-way ride. After you pay for your first ride, the app offers you a return booking with the addresses already swapped for you.", "es": "Para el viaje de regreso, simplemente reserva un segundo viaje de ida. Después de pagar tu primer viaje, la app te ofrece una reserva de regreso con las direcciones ya intercambiadas.", "fr": "Pour le trajet retour, réservez simplement un deuxième trajet aller simple. Après avoir payé votre premier trajet, l'application vous propose une réservation retour avec les adresses déjà inversées.", "ar": "لرحلة العودة، ما عليك سوى حجز رحلة ذهاب ثانية. بعد دفعك لرحلتك الأولى، سيعرض لك التطبيق حجز عودة مع تبديل العناوين مسبقًا.",
  "pt": "Para a viagem de volta, basta reservar uma segunda viagem só de ida. Depois de pagar sua primeira viagem, o app oferece uma reserva de volta com os endereços já trocados.", "ur": "Return journey ke liye bas doosri one-way ride book karen. Pehli ride pay karne ke baad, app aapko return booking dega jisme addresses pehle se swap honge.", "hi": "वापसी यात्रा के लिए, बस दूसरी एकतरफ़ा सवारी बुक करें। अपनी पहली सवारी का भुगतान करने के बाद, ऐप आपको वापसी बुकिंग देगा जिसमें पते पहले से बदले हुए होंगे।", "bn": "ফেরার যাত্রার জন্য শুধু দ্বিতীয় একমুখী রাইড বুক করুন। প্রথম রাইডের পেমেন্টের পর অ্যাপ আপনাকে ফেরার বুকিং দেবে, যেখানে ঠিকানা আগেই বদলে দেওয়া থাকবে।",
  "ud": "واپسی کے لیے بس دوسری ایک طرفہ سواری بک کریں۔ پہلی سواری کی ادائیگی کے بعد ایپ آپ کو واپسی کی سواری بک کرنے کی پیشکش کرے گی جس میں پتے پہلے سے تبدیل کیے گئے ہوں گے", "zh": "返程只需再预订一次单程行程。在您支付首次行程费用后，应用会为您提供地址已互换的返程预订。", "de": "Für eine Rückfahrt buchen Sie einfach eine zweite einfache Fahrt. Nachdem Sie Ihre erste Fahrt bezahlt haben, bietet Ihnen die App eine Rückfahrt an, bei der die Adressen bereits vertauscht sind.", "it": "Per il viaggio di ritorno, prenota semplicemente una seconda corsa di sola andata. Dopo aver pagato la prima corsa, l'app ti offre una prenotazione di ritorno con gli indirizzi già scambiati.",
  "ru": "Для обратной поездки просто забронируйте вторую поездку в одну сторону. После оплаты первой поездки приложение предложит вам обратное бронирование с уже поменянными местами адресами.", "tr": "Dönüş yolculuğu için ikinci bir tek yönlü yolculuk rezerve etmeniz yeterli. İlk yolculuğunuz için ödeme yaptıktan sonra uygulama size adresleri zaten değiştirilmiş bir dönüş rezervasyonu sunar.", "ko": "귀환 여정은 두 번째 편도 이동을 예약하시면 됩니다. 첫 이동을 결제한 후 앱에서 주소가 이미 바뀐 귀환 예약을 제공합니다.", "ja": "帰りの乗車は、もう一度片道乗車を予約するだけです。最初の乗車のお支払い後、アプリで住所がすでに入れ替わった帰りの予約が提案されます。",
  "vi": "Đối với chuyến về, chỉ cần đặt một chuyến đi một chiều thứ hai. Sau khi bạn thanh toán cho chuyến đi đầu tiên, ứng dụng sẽ đề xuất cho bạn một đặt xe về với các địa chỉ đã được hoán đổi.", "fa": "برای برگشت، فقط یک سفر یک‌طرفهٔ دوم رزرو کنید. پس از پرداخت اولین سفر، برنامه پیشنهاد می‌کند سفر برگشت را با نشانی‌های جابه‌جاشده رزرو کنید", "th": "สำหรับเที่ยวกลับ เพียงจองการเดินทางเที่ยวเดียวครั้งที่สอง หลังจากคุณชำระเงินสำหรับการเดินทางครั้งแรก แอปจะเสนอการจองเที่ยวกลับพร้อมที่อยู่ที่สลับกันแล้วให้คุณ"
};

NOEL_I18N["chat.ans_book_app"] = {
  "en": "Enter your pickup and drop-off, date and time in the Book tab, choose your experience, and pay by card — your chauffeur is assigned right after payment.", "es": "Escribe tu recogida y destino, fecha y hora en la pestaña Reservar, elige tu experiencia y paga con tarjeta: tu chófer se asigna justo después del pago.", "fr": "Saisissez votre lieu de prise en charge et votre destination, la date et l'heure dans l'onglet Réserver, choisissez votre expérience et payez par carte — votre chauffeur est assigné juste après le paiement.", "ar": "أدخل مكان الاستلام والوصول والتاريخ والوقت في تبويب الحجز، واختر تجربتك، وادفع بالبطاقة — وسيتم تعيين سائقك مباشرة بعد الدفع.",
  "pt": "Informe embarque e destino, data e hora na aba Reservar, escolha sua experiência e pague com cartão — seu motorista é designado logo após o pagamento.", "ur": "Book tab mein apna pickup aur drop-off, date aur time likhen, apna experience chunen, aur card se pay karen — payment ke foran baad aapka chauffeur assign ho jayega.", "hi": "बुक टैब में अपना पिकअप और ड्रॉप-ऑफ़, तारीख और समय लिखें, अपना अनुभव चुनें, और कार्ड से भुगतान करें — भुगतान के तुरंत बाद आपका शॉफ़र नियुक्त हो जाएगा।", "bn": "বুক ট্যাবে আপনার পিকআপ ও ড্রপ-অফ, তারিখ ও সময় লিখুন, আপনার অভিজ্ঞতা বেছে নিন, এবং কার্ডে পেমেন্ট করুন — পেমেন্টের পরপরই আপনার শোফার নিয়োগ করা হবে।",
  "ud": "بکنگ ٹیب میں پک اپ اور ڈراپ آف کے پتے، تاریخ اور وقت درج کریں، اپنا تجربہ منتخب کریں اور کارڈ سے ادائیگی کریں — ادائیگی کے فوراً بعد آپ کا ڈرائیور مقرر ہو جائے گا", "zh": "请在“预订”选项卡中输入上车和下车地址、日期和时间，选择您的体验并用卡支付——付款后将立即为您指派司机。", "de": "Geben Sie Abhol- und Zielort, Datum und Uhrzeit im Tab „Buchen“ ein, wählen Sie Ihr Erlebnis und bezahlen Sie per Karte — Ihr Chauffeur wird direkt nach der Zahlung zugewiesen.", "it": "Inserisci il luogo di partenza e di destinazione, data e ora nella scheda Prenota, scegli la tua esperienza e paga con carta — il tuo chauffeur verrà assegnato subito dopo il pagamento.",
  "ru": "Введите адрес отправления и назначения, дату и время во вкладке «Бронирование», выберите класс и оплатите картой — шофёр будет назначен сразу после оплаты.", "tr": "Biniş ve varış adresinizi, tarih ve saati Rezervasyon sekmesine girin, deneyiminizi seçin ve kartla ödeyin — şoförünüz ödemeden hemen sonra atanır.", "ko": "예약 탭에 출발지와 목적지, 날짜와 시간을 입력하고 원하는 경험을 선택한 뒤 카드로 결제하세요. 결제 후 바로 쇼퍼가 배정됩니다.", "ja": "「予約」タブに出発地と目的地、日付と時刻を入力し、エクスペリエンスを選択してカードでお支払いください。お支払い後すぐにショファーが割り当てられます。",
  "vi": "Nhập địa chỉ đón và trả khách, ngày và giờ trong tab Đặt xe, chọn trải nghiệm của bạn và thanh toán bằng thẻ — tài xế của bạn sẽ được chỉ định ngay sau khi thanh toán.", "fa": "در زبانهٔ رزرو، نشانی‌های مبدا و مقصد، تاریخ و زمان را وارد کنید، تجربهٔ خود را انتخاب کنید و با کارت پرداخت کنید — رانندهٔ شما بلافاصله پس از پرداخت تعیین می‌شود", "th": "ป้อนที่อยู่ต้นทางและปลายทาง วันที่และเวลาในแท็บจอง เลือกประสบการณ์ของคุณและชำระเงินด้วยบัตร — คนขับของคุณจะได้รับมอบหมายทันทีหลังชำระเงิน"
};

NOEL_I18N["chat.greeting"] = {
  "en": "Hello, and welcome to Noel Chauffer. How can I help — cancellation, waiting time, or something about a ride?", "es": "Hola, bienvenido a Noel Chauffer. ¿Cómo puedo ayudarte: cancelación, tiempo de espera o algo sobre un viaje?", "fr": "Bonjour et bienvenue chez Noel Chauffer. Comment puis-je vous aider — annulation, temps d'attente ou autre chose sur un trajet ?", "ar": "مرحبًا بك في نويل شوفير. كيف يمكنني مساعدتك — الإلغاء أو وقت الانتظار أو شيء عن رحلة؟",
  "pt": "Olá, bem-vindo à Noel Chauffer. Como posso ajudar — cancelamento, tempo de espera ou algo sobre uma viagem?", "ur": "Hello, Noel Chauffer mein welcome. Main kaise madad kar sakta hoon — cancellation, waiting time, ya ride ke baare mein kuch?", "hi": "नमस्ते, नोएल शॉफ़र में स्वागत है। मैं कैसे मदद कर सकता हूँ — रद्दीकरण, प्रतीक्षा समय, या सवारी के बारे में कुछ?", "bn": "হ্যালো, নোয়েল শোফারে স্বাগতম। আমি কীভাবে সাহায্য করতে পারি — বাতিল, অপেক্ষার সময়, বা রাইড সম্পর্কে কিছু?",
  "ud": "ہیلو، Noel Chauffer میں خوش آمدید۔ میں کس طرح مدد کر سکتا ہوں — منسوخی، انتظار کا وقت، یا سواری کے بارے میں کچھ؟", "zh": "您好，欢迎来到 Noel Chauffer。我能帮您什么——取消、等候时间或关于行程的事？", "de": "Hallo und willkommen bei Noel Chauffer. Wie kann ich helfen — Stornierung, Wartezeit oder etwas zu einer Fahrt?", "it": "Ciao e benvenuto da Noel Chauffer. Come posso aiutarti — cancellazione, tempo di attesa o qualcosa su una corsa?",
  "ru": "Здравствуйте, добро пожаловать в Noel Chauffer. Чем я могу помочь — отмена, время ожидания или что-то о поездке?", "tr": "Merhaba, Noel Chauffer'a hoş geldiniz. Nasıl yardımcı olabilirim — iptal, bekleme süresi veya bir yolculuk hakkında bir şey mi?", "ko": "안녕하세요, Noel Chauffer에 오신 것을 환영합니다. 취소, 대기 시간 또는 이동에 대해 어떻게 도와드릴까요?", "ja": "こんにちは、Noel Chaufferへようこそ。キャンセル、待ち時間、乗車についてどのようにお手伝いできますか？",
  "vi": "Xin chào, chào mừng bạn đến với Noel Chauffer. Tôi có thể giúp gì — hủy xe, thời gian chờ, hay điều gì về chuyến đi?", "fa": "سلام، به Noel Chauffer خوش آمدید. چگونه می‌توانم کمک کنم — لغو، زمان انتظار یا چیزی دربارهٔ سفر؟", "th": "สวัสดี ยินดีต้อนรับสู่ Noel Chauffer ฉันช่วยอะไรได้บ้าง — การยกเลิก เวลารอ หรือเรื่องเกี่ยวกับการเดินทาง?"
};

NOEL_I18N["chat.ans_paused"] = {
  "en": "No — bookings are open. Enter your pickup and drop-off in the booking form to see your fare.", "es": "No, las reservas están abiertas. Escribe tu recogida y destino en el formulario de reserva para ver tu tarifa.", "fr": "Non — les réservations sont ouvertes. Saisissez votre lieu de prise en charge et votre destination dans le formulaire pour voir votre tarif.", "ar": "لا — الحجوزات مفتوحة. أدخل مكان الاستلام والوصول في نموذج الحجز لترى أجرتك.",
  "pt": "Não — as reservas estão abertas. Informe embarque e destino no formulário de reserva para ver sua tarifa.", "ur": "Nahi — bookings khuli hain. Apna pickup aur drop-off booking form mein likhen to fare dikhega.", "hi": "नहीं — बुकिंग खुली है। अपना किराया देखने के लिए बुकिंग फ़ॉर्म में पिकअप और ड्रॉप-ऑफ़ लिखें।", "bn": "না — বুকিং খোলা আছে। ভাড়া দেখতে বুকিং ফর্মে আপনার পিকআপ ও ড্রপ-অফ লিখুন।",
  "ud": "نہیں — بکنگ کھلی ہوئی ہے۔ اپنا کرایہ دیکھنے کے لیے بکنگ فارم میں پک اپ اور ڈراپ آف کے پتے درج کریں", "zh": "没有——预订已开放。请在预订表格中输入上车和下车地址以查看价格。", "de": "Nein — Buchungen sind geöffnet. Geben Sie Abhol- und Zielort in das Buchungsformular ein, um Ihren Preis zu sehen.", "it": "No — le prenotazioni sono aperte. Inserisci il luogo di partenza e di destinazione nel modulo di prenotazione per vedere la tua tariffa.",
  "ru": "Нет — бронирование открыто. Введите адрес отправления и назначения в форму бронирования, чтобы увидеть тариф.", "tr": "Hayır — rezervasyonlar açık. Ücretinizi görmek için biniş ve varış adresinizi rezervasyon formuna girin.", "ko": "아니요, 예약이 가능합니다. 요금을 보려면 예약 양식에 출발지와 목적지를 입력하세요.", "ja": "いいえ、予約は受付中です。料金を見るには予約フォームに出発地と目的地を入力してください。",
  "vi": "Không — đặt xe đang mở. Nhập địa chỉ đón và trả khách vào biểu mẫu đặt xe để xem giá của bạn.", "fa": "خیر — رزرو باز است. برای مشاهدهٔ کرایه، نشانی‌های مبدا و مقصد را در فرم رزرو وارد کنید", "th": "ไม่ — การจองเปิดอยู่ ป้อนที่อยู่ต้นทางและปลายทางในแบบฟอร์มการจองเพื่อดูค่าโดยสารของคุณ"
};

NOEL_I18N["chat.ans_cancel"] = {
  "en": "Cancellation is free if you cancel more than 1 hour before pickup. If you cancel 1 hour or less before pickup, the cancellation is not refundable.", "es": "La cancelación es gratis si cancelas más de 1 hora antes de la recogida. Si cancelas 1 hora o menos antes, no es reembolsable.", "fr": "L'annulation est gratuite si vous annulez plus d'1 heure avant la prise en charge. Si vous annulez 1 heure ou moins avant, elle n'est pas remboursable.", "ar": "الإلغاء مجاني إذا ألغيت قبل أكثر من ساعة من الاستلام. أما إذا ألغيت قبل ساعة أو أقل من الاستلام، فلا يُسترد المبلغ.",
  "pt": "O cancelamento é gratuito se você cancelar mais de 1 hora antes do embarque. Se cancelar 1 hora ou menos antes, não é reembolsável.", "ur": "Cancellation free hai agar aap pickup se 1 hour se zyada pehle cancel karen. Agar 1 hour ya us se kam pehle cancel karen to refund nahi milega.", "hi": "पिकअप से 1 घंटे से ज़्यादा पहले रद्द करने पर रद्दीकरण मुफ़्त है। यदि आप पिकअप से 1 घंटे या उससे कम पहले रद्द करते हैं, तो यह वापस नहीं होगा।", "bn": "পিকআপের ১ ঘণ্টার বেশি আগে বাতিল করলে বাতিল বিনামূল্যে। পিকআপের ১ ঘণ্টা বা তার কম আগে বাতিল করলে তা ফেরতযোগ্য নয়।",
  "ud": "اگر آپ پک اپ کے وقت سے 1 گھنٹہ سے زیادہ پہلے منسوخ کریں تو مفت ہے۔ اگر آپ پک اپ کے 1 گھنٹہ یا اس سے کم وقت پہلے منسوخ کریں تو رقم واپس نہیں ہوگی", "zh": "在上车前1小时以上取消是免费的。如果在上车前1小时或更短时间内取消，则不予退款。", "de": "Die Stornierung ist kostenlos, wenn Sie mehr als 1 Stunde vor der Abholung stornieren. Wenn Sie 1 Stunde oder weniger vor der Abholung stornieren, ist die Stornierung nicht erstattungsfähig.", "it": "La cancellazione è gratuita se annulli più di 1 ora prima del ritiro. Se annulli 1 ora o meno prima del ritiro, la cancellazione non è rimborsabile.",
  "ru": "Отмена бесплатна, если вы отменяете более чем за 1 час до подачи. Если вы отменяете за 1 час или менее до подачи, отмена не возмещается.", "tr": "Binişten 1 saatten fazla süre önce iptal ederseniz iptal ücretsizdir. Binişten 1 saat veya daha az süre önce iptal ederseniz iptal iade edilmez.", "ko": "픽업 1시간 전에 취소하면 무료입니다. 픽업 1시간 이내에 취소하면 환불되지 않습니다.", "ja": "乗車の1時間以上前にキャンセルすれば無料です。乗車の1時間以内にキャンセルした場合、返金されません。",
  "vi": "Hủy miễn phí nếu bạn hủy hơn 1 giờ trước giờ đón. Nếu bạn hủy 1 giờ hoặc ít hơn trước giờ đón, việc hủy sẽ không được hoàn tiền.", "fa": "اگر بیش از ۱ ساعت پیش از زمان سوارشدن لغو کنید، رایگان است. اگر ۱ ساعت یا کمتر پیش از زمان سوارشدن لغو کنید، مبلغ بازپرداخت نمی‌شود", "th": "ยกเลิกฟรีหากคุณยกเลิกมากกว่า 1 ชั่วโมงก่อนเวลารับ หากคุณยกเลิก 1 ชั่วโมงหรือน้อยกว่าก่อนเวลารับ การยกเลิกจะไม่ได้รับเงินคืน"
};

NOEL_I18N["chat.ans_wait"] = {
  "en": "Waiting is free for 60 minutes at airports and 15 minutes at other pickups. After that, waiting charges apply.", "es": "La espera es gratis 60 minutos en aeropuertos y 15 minutos en otras recogidas. Después, se aplican cargos por espera.", "fr": "L'attente est gratuite pendant 60 minutes aux aéroports et 15 minutes aux autres prises en charge. Ensuite, des frais d'attente s'appliquent.", "ar": "الانتظار مجاني لمدة 60 دقيقة في المطارات و15 دقيقة في عمليات الاستلام الأخرى. بعد ذلك، تُطبق رسوم الانتظار.",
  "pt": "A espera é gratuita por 60 minutos em aeroportos e 15 minutos em outros embarques. Depois disso, taxas de espera se aplicam.", "ur": "Waiting airports par 60 minutes aur doosri pickups par 15 minutes free hai. Uske baad waiting charges lagte hain.", "hi": "एयरपोर्ट पर 60 मिनट और अन्य पिकअप पर 15 मिनट तक प्रतीक्षा मुफ़्त है। उसके बाद प्रतीक्षा शुल्क लगता है।", "bn": "বিমানবন্দরে ৬০ মিনিট এবং অন্যান্য পিকআপে ১৫ মিনিট পর্যন্ত অপেক্ষা বিনামূল্যে। এরপর অপেক্ষার চার্জ প্রযোজ্য।",
  "ud": "ہوائی اڈے پر 60 منٹ اور دیگر پک اپ جگہوں پر 15 منٹ مفت انتظار ہے، اس کے بعد انتظار کا چارج لگے گا", "zh": "机场免费等候60分钟，其他上车点免费等候15分钟。此后将收取等候费用。", "de": "Die Wartezeit ist an Flughäfen 60 Minuten und bei anderen Abholungen 15 Minuten kostenlos. Danach fallen Wartegebühren an.", "it": "L'attesa è gratuita per 60 minuti negli aeroporti e 15 minuti per gli altri ritiri. Dopo di che, si applicano le tariffe di attesa.",
  "ru": "Ожидание бесплатно 60 минут в аэропортах и 15 минут при других подачах. После этого взимается плата за ожидание.", "tr": "Havalimanlarında 60 dakika, diğer binişlerde 15 dakika bekleme ücretsizdir. Sonrasında bekleme ücreti uygulanır.", "ko": "공항에서는 60분, 다른 픽업 장소에서는 15분까지 대기 무료입니다. 이후에는 대기 요금이 부과됩니다.", "ja": "空港では60分、その他の乗車では15分まで待ち時間は無料です。その後は待ち料金がかかります。",
  "vi": "Chờ miễn phí 60 phút tại sân bay và 15 phút tại các điểm đón khác. Sau đó, phí chờ sẽ được áp dụng.", "fa": "در فرودگاه ۶۰ دقیقه و در دیگر نقاط سوارشدن ۱۵ دقیقه انتظار رایگان است، پس از آن هزینهٔ انتظار اعمال می‌شود", "th": "รอฟรี 60 นาทีที่สนามบินและ 15 นาทีที่จุดรับอื่น หลังจากนั้นจะคิดค่ารอ"
};

NOEL_I18N["chat.ans_price"] = {
  "en": "Enter your pickup and drop-off in the booking form above, choose your experience, and you will see the total for each class before you pay.", "es": "Escribe tu recogida y destino en el formulario de arriba, elige tu experiencia y verás el total de cada clase antes de pagar.", "fr": "Saisissez votre lieu de prise en charge et votre destination dans le formulaire ci-dessus, choisissez votre expérience et vous verrez le total de chaque classe avant de payer.", "ar": "أدخل مكان الاستلام والوصول في نموذج الحجز أعلاه، واختر تجربتك، وسترى المجموع لكل فئة قبل الدفع.",
  "pt": "Informe embarque e destino no formulário acima, escolha sua experiência e você verá o total de cada classe antes de pagar.", "ur": "Upar booking form mein apna pickup aur drop-off likhen, apna experience chunen, aur pay karne se pehle har class ka total dekh lenge.", "hi": "ऊपर बुकिंग फ़ॉर्म में अपना पिकअप और ड्रॉप-ऑफ़ लिखें, अपना अनुभव चुनें, और भुगतान से पहले आप हर श्रेणी का कुल देखेंगे।", "bn": "উপরের বুকিং ফর্মে আপনার পিকআপ ও ড্রপ-অফ লিখুন, আপনার অভিজ্ঞতা বেছে নিন, এবং পেমেন্টের আগে প্রতিটি শ্রেণির মোট দেখতে পাবেন।",
  "ud": "اوپر والے بکنگ فارم میں پک اپ اور ڈراپ آف کے پتے درج کریں، اپنا تجربہ منتخب کریں، اور ادائیگی سے پہلے آپ کو ہر کلاس کی کل رقم نظر آ جائے گی", "zh": "请在上方预订表格中输入上车和下车地址，选择您的体验，付款前您将看到每个级别的总价。", "de": "Geben Sie Abhol- und Zielort in das Buchungsformular oben ein, wählen Sie Ihr Erlebnis und Sie sehen den Gesamtpreis für jede Klasse, bevor Sie bezahlen.", "it": "Inserisci il luogo di partenza e di destinazione nel modulo di prenotazione sopra, scegli la tua esperienza e vedrai il totale per ogni classe prima di pagare.",
  "ru": "Введите адрес отправления и назначения в форму бронирования выше, выберите класс, и вы увидите общую стоимость для каждого класса перед оплатой.", "tr": "Yukarıdaki rezervasyon formuna biniş ve varış adresinizi girin, deneyiminizi seçin; ödemeden önce her sınıf için toplamı göreceksiniz.", "ko": "위의 예약 양식에 출발지와 목적지를 입력하고 경험을 선택하면 결제 전에 각 클래스별 총액을 확인할 수 있습니다.", "ja": "上記の予約フォームに出発地と目的地を入力し、エクスペリエンスを選択すると、お支払い前に各クラスの合計が表示されます。",
  "vi": "Nhập địa chỉ đón và trả khách vào biểu mẫu đặt xe ở trên, chọn trải nghiệm của bạn và bạn sẽ thấy tổng giá cho mỗi hạng trước khi thanh toán.", "fa": "در فرم رزرو بالا، نشانی‌های مبدا و مقصد را وارد کنید، تجربهٔ خود را انتخاب کنید و پیش از پرداخت، مجموع هر کلاس را خواهید دید", "th": "ป้อนที่อยู่ต้นทางและปลายทางในแบบฟอร์มการจองด้านบน เลือกประสบการณ์ของคุณ แล้วคุณจะเห็นยอดรวมของแต่ละระดับก่อนชำระเงิน"
};

NOEL_I18N["chat.ans_lost"] = {
  "en": "I am sorry to hear that. Please report it here as soon as you can, and within 7 days. The driver checks the car after every ride. Unclaimed items go to the police station after one week.", "es": "Lamento oírlo. Repórtalo aquí lo antes posible, dentro de 7 días. El chófer revisa el coche después de cada viaje. Los objetos no reclamados van a la comisaría después de una semana.", "fr": "Je suis désolé d'apprendre cela. Veuillez le signaler ici dès que possible, sous 7 jours. Le chauffeur vérifie la voiture après chaque trajet. Les objets non réclamés sont remis au commissariat après une semaine.", "ar": "يؤسفني سماع ذلك. يرجى الإبلاغ عنه هنا في أقرب وقت ممكن وخلال 7 أيام. يفحص السائق السيارة بعد كل رحلة. وتُسلَّم الأغراض غير المطالب بها إلى مركز الشرطة بعد أسبوع.",
  "pt": "Sinto muito por isso. Relate aqui o quanto antes, em até 7 dias. O motorista verifica o carro após cada viagem. Itens não reclamados vão para a delegacia após uma semana.", "ur": "Sun kar afsos hua. Jitni jaldi ho sake yahin report karen, 7 din ke andar. Driver har ride ke baad gaadi check karta hai. Ek hafte ke baad bina daawe wali cheezein police station chali jati hain.", "hi": "यह सुनकर दुख हुआ। कृपया इसे जल्द से जल्द, 7 दिनों के भीतर, यहीं रिपोर्ट करें। ड्राइवर हर सवारी के बाद गाड़ी जाँचता है। एक सप्ताह बाद बिना दावे वाली चीज़ें पुलिस स्टेशन चली जाती हैं।", "bn": "শুনে দুঃখিত হলাম। যত তাড়াতাড়ি সম্ভব, ৭ দিনের মধ্যে এখানে জানান। ড্রাইভার প্রতিটি রাইডের পর গাড়ি পরীক্ষা করেন। এক সপ্তাহ পর দাবিহীন জিনিস থানায় পাঠানো হয়।",
  "ud": "معذرت، براہ کرم جلد از جلد اور 7 دنوں کے اندر یہاں بتائیں۔ ڈرائیور ہر سواری کے بعد گاڑی چیک کرتا ہے۔ جن چیزوں کا دعویٰ نہ کیا جائے وہ ایک ہفتے بعد پولیس اسٹیشن بھیج دی جاتی ہیں", "zh": "很抱歉听到这个消息。请尽快并在7天内在此报告。司机每次行程后都会检查车辆。无人认领的物品一周后将交到警察局。", "de": "Das tut mir leid. Bitte melden Sie es hier so schnell wie möglich und innerhalb von 7 Tagen. Der Fahrer überprüft das Auto nach jeder Fahrt. Nicht abgeholte Gegenstände gehen nach einer Woche an die Polizeistation.", "it": "Mi dispiace. Segnalalo qui il prima possibile ed entro 7 giorni. L'autista controlla l'auto dopo ogni corsa. Gli oggetti non reclamati vanno alla stazione di polizia dopo una settimana.",
  "ru": "Мне очень жаль. Пожалуйста, сообщите об этом здесь как можно скорее и в течение 7 дней. Водитель проверяет автомобиль после каждой поездки. Невостребованные вещи через неделю передаются в полицейский участок.", "tr": "Üzüldüm. Lütfen bunu burada mümkün olan en kısa sürede ve 7 gün içinde bildirin. Sürücü her yolculuktan sonra aracı kontrol eder. Sahipsiz eşyalar bir hafta sonra karakola teslim edilir.", "ko": "안타깝습니다. 가능한 한 빨리, 7일 이내에 여기에 신고해 주세요. 기사는 매 이동 후 차량을 확인합니다. 찾아가지 않은 물품은 일주일 후 경찰서로 넘어갑니다.", "ja": "申し訳ございません。できるだけ早く、7日以内にこちらにご報告ください。ドライバーは毎回の乗車後に車内を確認します。引き取りのない忘れ物は1週間後に警察署に届けられます。",
  "vi": "Tôi rất tiếc khi nghe điều đó. Vui lòng báo cáo tại đây càng sớm càng tốt và trong vòng 7 ngày. Tài xế kiểm tra xe sau mỗi chuyến đi. Đồ không ai nhận sẽ được giao cho đồn cảnh sát sau một tuần.", "fa": "متاسفم، لطفاً هرچه زودتر و ظرف ۷ روز اینجا اطلاع دهید. راننده پس از هر سفر خودرو را بررسی می‌کند. وسایلی که کسی آن‌ها را تحویل نگیرد پس از یک هفته به ایستگاه پلیس فرستاده می‌شود", "th": "เสียใจด้วย โปรดแจ้งที่นี่โดยเร็วที่สุดและภายใน 7 วัน คนขับจะตรวจรถหลังการเดินทางทุกครั้ง ของที่ไม่มีผู้มารับจะถูกส่งไปที่สถานีตำรวจหลังจากหนึ่งสัปดาห์"
};

NOEL_I18N["chat.ans_problem"] = {
  "en": "I am sorry about that. I will escalate this to the owner, who will look into it personally. Please tell me your pickup date and time and what happened.", "es": "Lo siento. Escalaré esto al propietario, que lo revisará personalmente. Dime la fecha y hora de tu recogida y qué pasó.", "fr": "Je suis désolé. Je vais transmettre cela au propriétaire, qui s'en occupera personnellement. Indiquez-moi la date et l'heure de votre prise en charge et ce qui s'est passé.", "ar": "أنا آسف لذلك. سأصعّد الأمر إلى المالك، الذي سينظر فيه بنفسه. يرجى إخباري بتاريخ ووقت الاستلام وما حدث.",
  "pt": "Sinto muito por isso. Vou escalar para o proprietário, que vai analisar pessoalmente. Informe a data e a hora do embarque e o que aconteceu.", "ur": "Is ke liye maazrat. Main ye owner tak pahuncha doonga, jo khud dekhenge. Apni pickup ki date aur time aur kya hua, ye bata den.", "hi": "इसके लिए खेद है। मैं इसे मालिक तक पहुँचाऊँगा, जो इसे व्यक्तिगत रूप से देखेंगे। कृपया अपनी पिकअप तिथि और समय तथा क्या हुआ, बताएँ।", "bn": "এর জন্য দুঃখিত। আমি এটি মালিকের কাছে পাঠাব, যিনি নিজে দেখবেন। আপনার পিকআপের তারিখ ও সময় এবং কী ঘটেছে তা জানান।",
  "ud": "معذرت، میں یہ معاملہ مالک کو بھیج دوں گا جو اسے خود دیکھے گا۔ براہ کرم اپنی پک اپ کی تاریخ اور وقت اور جو کچھ ہوا وہ بتائیں", "zh": "很抱歉。我会将此事上报给负责人，他会亲自处理。请告诉我您的上车日期和时间以及发生了什么。", "de": "Das tut mir leid. Ich werde dies an den Inhaber weiterleiten, der sich persönlich darum kümmern wird. Bitte nennen Sie mir Ihr Abholdatum, Ihre Abholzeit und was passiert ist.", "it": "Mi dispiace. Lo inoltrerò al proprietario, che se ne occuperà personalmente. Dimmi la data e l'ora del ritiro e cosa è successo.",
  "ru": "Мне очень жаль. Я передам это владельцу, который лично разберётся. Пожалуйста, сообщите мне дату и время подачи и что произошло.", "tr": "Bunun için üzgünüm. Bunu bizzat ilgilenecek olan sahibine ileteceğim. Lütfen biniş tarihinizi ve saatinizi ve ne olduğunu söyleyin.", "ko": "죄송합니다. 직접 살펴볼 소유자에게 전달하겠습니다. 픽업 날짜와 시간, 무슨 일이 있었는지 알려주세요.", "ja": "申し訳ございません。直接対応するオーナーにエスカレーションします。乗車の日付と時刻、何が起きたかをお知らせください。",
  "vi": "Tôi rất tiếc về điều đó. Tôi sẽ chuyển vấn đề này lên cho chủ sở hữu, người sẽ tự mình xem xét. Vui lòng cho tôi biết ngày và giờ đón của bạn và chuyện gì đã xảy ra.", "fa": "متاسفم، این موضوع را به مالک ارجاع می‌دهم تا شخصاً رسیدگی کند. لطفاً تاریخ و زمان سوارشدن خود و آنچه اتفاق افتاده را بگویید", "th": "เสียใจด้วย ฉันจะส่งเรื่องนี้ให้เจ้าของซึ่งจะดูแลด้วยตนเอง โปรดบอกวันที่และเวลารับของคุณและสิ่งที่เกิดขึ้น"
};

NOEL_I18N["chat.ans_driver"] = {
  "en": "As soon as your chauffeur accepts, you will see their name, phone number, car, colour and plate number on this page — and the same details are sent to your phone and email.", "es": "En cuanto tu chófer acepte, verás su nombre, número de teléfono, coche, color y matrícula en esta página, y los mismos datos se enviarán a tu teléfono y correo.", "fr": "Dès que votre chauffeur accepte, vous verrez son nom, son numéro de téléphone, sa voiture, sa couleur et sa plaque sur cette page — et ces mêmes informations seront envoyées sur votre téléphone et par e-mail.", "ar": "بمجرد أن يقبل سائقك، سترى اسمه ورقم هاتفه وسيارته ولونها ورقم لوحتها على هذه الصفحة — وستُرسل التفاصيل نفسها إلى هاتفك وبريدك الإلكتروني.",
  "pt": "Assim que seu motorista aceitar, você verá o nome, o telefone, o carro, a cor e a placa dele nesta página — e os mesmos dados serão enviados para seu telefone e e-mail.", "ur": "Jaise hi aapka chauffeur accept karega, aapko is page par unka naam, phone number, gaadi, colour aur plate number dikhega — aur yehi details aapke phone aur email par bhi bheji jayengi.", "hi": "जैसे ही आपका शॉफ़र स्वीकार करेगा, आपको इस पेज पर उनका नाम, फ़ोन नंबर, गाड़ी, रंग और नंबर प्लेट दिखेगा — और यही जानकारी आपके फ़ोन और ईमेल पर भी भेजी जाएगी।", "bn": "আপনার শোফার গ্রহণ করলেই এই পাতায় তাঁর নাম, ফোন নম্বর, গাড়ি, রং ও নম্বর প্লেট দেখতে পাবেন — আর একই বিবরণ আপনার ফোন ও ইমেইলে পাঠানো হবে।",
  "ud": "جیسے ہی آپ کا ڈرائیور قبول کرے گا، آپ کو اس صفحے پر اس کا نام، فون نمبر، گاڑی، رنگ اور پلیٹ نمبر نظر آئے گا — اور وہی تفصیلات آپ کے فون اور ای میل پر بھی بھیجی جائیں گی", "zh": "司机接受订单后，您将在此页面看到他的姓名、电话号码、车辆、颜色和车牌号——相同信息也会发送到您的手机和邮箱。", "de": "Sobald Ihr Chauffeur akzeptiert, sehen Sie seinen Namen, seine Telefonnummer, sein Auto, seine Farbe und sein Kennzeichen auf dieser Seite — und dieselben Daten werden an Ihr Telefon und Ihre E-Mail-Adresse gesendet.", "it": "Non appena il tuo chauffeur accetta, vedrai il suo nome, numero di telefono, auto, colore e numero di targa in questa pagina — e gli stessi dati verranno inviati al tuo telefono e alla tua email.",
  "ru": "Как только ваш шофёр примет заказ, вы увидите его имя, номер телефона, автомобиль, цвет и номерной знак на этой странице — и те же данные будут отправлены на ваш телефон и электронную почту.", "tr": "Şoförünüz kabul eder etmez adını, telefon numarasını, aracını, rengini ve plaka numarasını bu sayfada göreceksiniz — aynı bilgiler telefonunuza ve e-postanıza da gönderilir.", "ko": "쇼퍼가 수락하는 즉시 이 페이지에서 이름, 전화번호, 차량, 색상, 번호판을 확인할 수 있으며 같은 정보가 휴대폰과 이메일로도 전송됩니다.", "ja": "ショファーが承諾すると、このページに名前、電話番号、車、色、ナンバープレートが表示されます。同じ詳細がお客様の電話とメールにも送信されます。",
  "vi": "Ngay khi tài xế của bạn chấp nhận, bạn sẽ thấy tên, số điện thoại, xe, màu sắc và biển số của họ trên trang này — và các thông tin tương tự cũng được gửi đến điện thoại và email của bạn.", "fa": "به‌محض اینکه رانندهٔ شما قبول کند، نام، شماره تلفن، خودرو، رنگ و پلاک او را در همین صفحه خواهید دید — و همان جزئیات به تلفن و ایمیل شما نیز ارسال می‌شود", "th": "ทันทีที่คนขับของคุณตอบรับ คุณจะเห็นชื่อ หมายเลขโทรศัพท์ รถยนต์ สี และหมายเลขทะเบียนบนหน้านี้ — และรายละเอียดเดียวกันจะถูกส่งไปยังโทรศัพท์และอีเมลของคุณ"
};

NOEL_I18N["chat.ans_car"] = {
  "en": "Our rides come in three classes — Business Class, Business SUV and First Class — recent high-end cars, clean, comfortable, and prepared for every ride, with phone chargers on board.", "es": "Nuestros viajes vienen en tres clases: Business Class, Business SUV y First Class. Coches recientes de alta gama, limpios, cómodos y preparados para cada viaje, con cargadores de teléfono a bordo.", "fr": "Nos trajets existent en trois classes — Business Class, Business SUV et First Class — des voitures récentes haut de gamme, propres, confortables et préparées pour chaque trajet, avec des chargeurs de téléphone à bord.", "ar": "رحلاتنا تأتي في ثلاث فئات — Business Class وBusiness SUV وFirst Class — سيارات حديثة فاخرة، نظيفة ومريحة ومجهزة لكل رحلة، مع شواحن هواتف على متنها.",
  "pt": "Nossas viagens têm três classes — Business Class, Business SUV e First Class — carros recentes de alto padrão, limpos, confortáveis e preparados para cada viagem, com carregadores de celular a bordo.", "ur": "Hamari rides teen classes mein aati hain — Business Class, Business SUV aur First Class — nayi high-end gaadiyan, saaf, aaramdeh, har ride ke liye ready, aur onboard phone chargers ke saath.", "hi": "हमारी सवारियाँ तीन श्रेणियों में आती हैं — Business Class, Business SUV और First Class — नई उच्च-स्तरीय गाड़ियाँ, साफ़, आरामदायक, हर सवारी के लिए तैयार, और ऑनबोर्ड फ़ोन चार्जर के साथ।", "bn": "আমাদের রাইড তিনটি শ্রেণিতে আসে — Business Class, Business SUV ও First Class — নতুন উঁচুমানের গাড়ি, পরিষ্কার, আরামদায়ক, প্রতিটি রাইডের জন্য প্রস্তুত, এবং অনবোর্ড ফোন চার্জারসহ।",
  "ud": "ہمارے پاس تین کلاسیں ہیں — Business Class، Business SUV اور First Class — نئی، صاف ستھری، آرام دہ لگژری گاڑیاں، ہر سواری کے لیے تیار، گاڑی میں فون چارجر کے ساتھ", "zh": "我们的行程分为三个级别——Business Class、Business SUV 和 First Class——均为较新的高端车辆，干净、舒适，为每次行程做好准备，车上配有手机充电器。", "de": "Unsere Fahrten gibt es in drei Klassen — Business Class, Business SUV und First Class — neueste hochwertige Autos, sauber, komfortabel und für jede Fahrt vorbereitet, mit Handyladegeräten an Bord.", "it": "Le nostre corse sono in tre classi — Business Class, Business SUV e First Class — auto recenti di fascia alta, pulite, confortevoli e preparate per ogni corsa, con caricabatterie a bordo.",
  "ru": "Наши поездки бывают трёх классов — Business Class, Business SUV и First Class — новые автомобили высокого класса, чистые, комфортабельные и подготовленные к любой поездке, с зарядными устройствами на борту.", "tr": "Yolculuklarımız üç sınıfta sunulur — Business Class, Business SUV ve First Class — yeni üst sınıf araçlar, temiz, konforlu ve her yolculuğa hazır, araçta telefon şarj cihazlarıyla.", "ko": "이동은 세 가지 클래스로 제공됩니다 — Business Class, Business SUV, First Class — 최신 고급 차량으로 깨끗하고 편안하며 모든 이동에 대비되어 있고 차량 내 휴대폰 충전기가 마련되어 있습니다.", "ja": "乗車は3つのクラスがあります — Business Class、Business SUV、First Class — 最新の高級車、清潔で快適、すべての乗車に備え、車内には電話充電器があります。",
  "vi": "Chuyến đi của chúng tôi có ba hạng — Business Class, Business SUV và First Class — xe cao cấp đời mới, sạch sẽ, thoải mái và được chuẩn bị cho mọi chuyến đi, với bộ sạc điện thoại trên xe.", "fa": "ما سه کلاس داریم — Business Class، Business SUV و First Class — خودروهای لوکس جدید، تمیز، راحت و آماده برای هر سفر، با شارژر تلفن در خودرو", "th": "การเดินทางของเรามีสามระดับ — Business Class, Business SUV และ First Class — รถยนต์ระดับสูงรุ่นใหม่ สะอาด สะดวกสบาย และเตรียมพร้อมสำหรับการเดินทางทุกครั้ง พร้อมที่ชาร์จโทรศัพท์ในรถ"
};

NOEL_I18N["chat.ans_return"] = {
  "en": "For a return journey, simply book a second one-way ride. After you pay for your first ride, this page offers you a return booking with the addresses already swapped for you.", "es": "Para el viaje de regreso, simplemente reserva un segundo viaje de ida. Después de pagar tu primer viaje, esta página te ofrece una reserva de regreso con las direcciones ya intercambiadas.", "fr": "Pour le trajet retour, réservez simplement un deuxième trajet aller simple. Après avoir payé votre premier trajet, cette page vous propose une réservation retour avec les adresses déjà inversées.", "ar": "لرحلة العودة، ما عليك سوى حجز رحلة ذهاب ثانية. بعد دفعك لرحلتك الأولى، ستعرض لك هذه الصفحة حجز عودة مع تبديل العناوين مسبقًا.",
  "pt": "Para a viagem de volta, basta reservar uma segunda viagem só de ida. Depois de pagar sua primeira viagem, esta página oferece uma reserva de volta com os endereços já trocados.", "ur": "Return journey ke liye bas doosri one-way ride book karen. Pehli ride pay karne ke baad, ye page aapko return booking dega jisme addresses pehle se swap honge.", "hi": "वापसी यात्रा के लिए, बस दूसरी एकतरफ़ा सवारी बुक करें। अपनी पहली सवारी का भुगतान करने के बाद, यह पेज आपको वापसी बुकिंग देगा जिसमें पते पहले से बदले हुए होंगे।", "bn": "ফেরার যাত্রার জন্য শুধু দ্বিতীয় একমুখী রাইড বুক করুন। প্রথম রাইডের পেমেন্টের পর এই পাতায় ফেরার বুকিং পাবেন, যেখানে ঠিকানা আগেই বদলে দেওয়া থাকবে।",
  "ud": "واپسی کے لیے بس دوسری ایک طرفہ سواری بک کریں۔ پہلی سواری کی ادائیگی کے بعد یہ صفحہ آپ کو واپسی کی سواری بک کرنے کی پیشکش کرے گا جس میں پتے پہلے سے تبدیل کیے گئے ہوں گے", "zh": "返程只需再预订一次单程行程。在您支付首次行程费用后，本页面会为您提供地址已互换的返程预订。", "de": "Für eine Rückfahrt buchen Sie einfach eine zweite einfache Fahrt. Nachdem Sie Ihre erste Fahrt bezahlt haben, bietet Ihnen diese Seite eine Rückfahrt an, bei der die Adressen bereits vertauscht sind.", "it": "Per il viaggio di ritorno, prenota semplicemente una seconda corsa di sola andata. Dopo aver pagato la prima corsa, questa pagina ti offre una prenotazione di ritorno con gli indirizzi già scambiati.",
  "ru": "Для обратной поездки просто забронируйте вторую поездку в одну сторону. После оплаты первой поездки эта страница предложит вам обратное бронирование с уже поменянными местами адресами.", "tr": "Dönüş yolculuğu için ikinci bir tek yönlü yolculuk rezerve etmeniz yeterli. İlk yolculuğunuz için ödeme yaptıktan sonra bu sayfa size adresleri zaten değiştirilmiş bir dönüş rezervasyonu sunar.", "ko": "귀환 여정은 두 번째 편도 이동을 예약하시면 됩니다. 첫 이동을 결제한 후 이 페이지에서 주소가 이미 바뀐 귀환 예약을 제공합니다.", "ja": "帰りの乗車は、もう一度片道乗車を予約するだけです。最初の乗車のお支払い後、このページで住所がすでに入れ替わった帰りの予約が提案されます。",
  "vi": "Đối với chuyến về, chỉ cần đặt một chuyến đi một chiều thứ hai. Sau khi bạn thanh toán cho chuyến đi đầu tiên, trang này sẽ đề xuất cho bạn một đặt xe về với các địa chỉ đã được hoán đổi.", "fa": "برای برگشت، فقط یک سفر یک‌طرفهٔ دوم رزرو کنید. پس از پرداخت اولین سفر، این صفحه پیشنهاد می‌کند سفر برگشت را با نشانی‌های جابه‌جاشده رزرو کنید", "th": "สำหรับเที่ยวกลับ เพียงจองการเดินทางเที่ยวเดียวครั้งที่สอง หลังจากคุณชำระเงินสำหรับการเดินทางครั้งแรก หน้านี้จะเสนอการจองเที่ยวกลับพร้อมที่อยู่ที่สลับกันแล้วให้คุณ"
};

NOEL_I18N["chat.ans_hourly"] = {
  "en": "Choose the “By the hour” tab in the booking form, pick a vehicle class and how many hours you need (minimum 2 hours). Your chauffeur stays with you for the hours you book, with 25 miles of travel included per hour.", "es": "Elige la pestaña «Por horas» en el formulario de reserva, escoge una clase de vehículo y cuántas horas necesitas (mínimo 2 horas). Tu chófer se queda contigo las horas que reserves, con 25 millas de viaje incluidas por hora.", "fr": "Choisissez l'onglet « À l'heure » dans le formulaire de réservation, sélectionnez une classe de véhicule et le nombre d'heures nécessaires (minimum 2 heures). Votre chauffeur reste avec vous pendant les heures réservées, avec 25 miles de trajet inclus par heure.", "ar": "اختر تبويب «بالساعة» في نموذج الحجز، واختر فئة المركبة وعدد الساعات التي تحتاجها (الحد الأدنى ساعتان). يبقى سائقك معك طوال الساعات التي تحجزها، مع 25 ميلًا من السفر مشمولة في الساعة.",
  "pt": "Escolha a aba “Por hora” no formulário de reserva, selecione uma classe de veículo e quantas horas você precisa (mínimo de 2 horas). Seu motorista fica com você pelas horas reservadas, com 25 milhas de viagem incluídas por hora.", "ur": "Booking form mein “By the hour” tab chunen, gaadi ki class aur kitne hours chahiye ye chunen (minimum 2 hours). Aapka chauffeur utne hours aapke saath rahega, har hour mein 25 miles travel shamil hai.", "hi": "बुकिंग फ़ॉर्म में “By the hour” टैब चुनें, वाहन की श्रेणी और कितने घंटे चाहिए, यह चुनें (न्यूनतम 2 घंटे)। आपका शॉफ़र आपके बुक किए घंटों तक आपके साथ रहेगा, प्रति घंटे 25 मील की यात्रा शामिल है।", "bn": "বুকিং ফর্মে “By the hour” ট্যাব বেছে নিন, গাড়ির শ্রেণি ও কত ঘণ্টা দরকার তা বেছে নিন (সর্বনিম্ন ২ ঘণ্টা)। আপনার শোফার আপনার বুক করা ঘণ্টাগুলো আপনার সঙ্গে থাকবেন, প্রতি ঘণ্টায় ২৫ মাইল ভ্রমণ অন্তর্ভুক্ত।",
  "ud": "بکنگ فارم میں “فی گھنٹہ” والا ٹیب منتخب کریں، گاڑی کی کلاس اور گھنٹوں کی تعداد منتخب کریں (کم از کم 2 گھنٹے)۔ آپ کا ڈرائیور بک کیے گئے تمام گھنٹوں کے لیے آپ کے ساتھ رہے گا، ہر گھنٹے 25 میل شامل ہیں", "zh": "请在预订表格中选择“按小时”选项卡，选择车辆级别和所需小时数（至少2小时）。在您预订的时间内司机将一直陪伴您，每小时包含25英里行程。", "de": "Wählen Sie im Buchungsformular den Tab „Stundenweise“, wählen Sie eine Fahrzeugklasse und wie viele Stunden Sie benötigen (mindestens 2 Stunden). Ihr Chauffeur bleibt für die von Ihnen gebuchten Stunden bei Ihnen, mit 25 Meilen Fahrt pro Stunde inklusive.", "it": "Scegli la scheda “A ore” nel modulo di prenotazione, scegli una classe di veicolo e quante ore ti servono (minimo 2 ore). Il tuo chauffeur resta con te per le ore prenotate, con 25 miglia di viaggio incluse all'ora.",
  "ru": "Выберите вкладку «Почасовая» в форме бронирования, выберите класс автомобиля и сколько часов вам нужно (минимум 2 часа). Ваш шофёр останется с вами на забронированные часы, включая 25 миль поездки в час.", "tr": "Rezervasyon formunda “Saatlik” sekmesini seçin, bir araç sınıfı ve kaç saat gerektiğini seçin (en az 2 saat). Şoförünüz rezerve ettiğiniz saatler boyunca sizinle kalır, saat başına 25 mil yolculuk dahildir.", "ko": "예약 양식에서 '시간제' 탭을 선택하고 차량 클래스와 필요한 시간(최소 2시간)을 선택하세요. 예약한 시간 동안 쇼퍼가 함께하며 시간당 25마일 이동이 포함됩니다.", "ja": "予約フォームの「時間貸し」タブを選択し、車両クラスと必要な時間（最低2時間）を選択してください。予約した時間、ショファーがお客様と一緒にいられ、1時間あたり25マイルの走行が含まれます。",
  "vi": "Chọn tab “Theo giờ” trong biểu mẫu đặt xe, chọn hạng xe và số giờ bạn cần (tối thiểu 2 giờ). Tài xế của bạn sẽ ở cùng bạn trong số giờ bạn đặt, bao gồm 25 dặm di chuyển mỗi giờ.", "fa": "در فرم رزرو، زبانهٔ «ساعتی» را انتخاب کنید، کلاس خودرو و تعداد ساعت‌ها را انتخاب کنید (حداقل ۲ ساعت). رانندهٔ شما در تمام ساعت‌های رزروشده نزد شما می‌ماند، با ۲۵ مایل در هر ساعت", "th": "เลือกแท็บ “รายชั่วโมง” ในแบบฟอร์มการจอง เลือกระดับรถยนต์และจำนวนชั่วโมงที่ต้องการ (ขั้นต่ำ 2 ชั่วโมง) คนขับของคุณจะอยู่กับคุณตลอดชั่วโมงที่จอง รวมระยะทาง 25 ไมล์ต่อชั่วโมง"
};

NOEL_I18N["chat.ans_refer"] = {
  "en": "If a friend referred you, open their referral link — it takes you to the booking form with their code already filled in, and your first booking gets 5% off.", "es": "Si un amigo te recomendó, abre su enlace de recomendación: te lleva al formulario de reserva con su código ya rellenado, y tu primera reserva tiene un 5 % de descuento.", "fr": "Si un ami vous a parrainé, ouvrez son lien de parrainage — il vous mène au formulaire de réservation avec son code déjà rempli, et votre première réservation bénéficie de 5 % de réduction.", "ar": "إذا أحالك صديق، افتح رابط الإحالة الخاص به — سيأخذك إلى نموذج الحجز ورمزه معبأ مسبقًا، وستحصل على خصم 5٪ على حجزك الأول.",
  "pt": "Se um amigo indicou você, abra o link de indicação dele — ele leva ao formulário de reserva com o código já preenchido, e sua primeira reserva tem 5% de desconto.", "ur": "Agar kisi dost ne refer kiya hai to unka referral link kholen — wo aapko booking form par le jayega jisme unka code pehle se bhara hoga, aur aapki pehli booking par 5% off milega.", "hi": "यदि किसी मित्र ने आपको रेफ़र किया है, तो उनका रेफ़रल लिंक खोलें — यह आपको बुकिंग फ़ॉर्म पर ले जाएगा जिसमें उनका कोड पहले से भरा होगा, और आपकी पहली बुकिंग पर 5% की छूट मिलेगी।", "bn": "যদি কোনো বন্ধু আপনাকে রেফার করে থাকেন, তাঁর রেফারেল লিংক খুলুন — এটি আপনাকে বুকিং ফর্মে নিয়ে যাবে যেখানে তাঁর কোড আগেই ভরা থাকবে, এবং আপনার প্রথম বুকিংয়ে ৫% ছাড় পাবেন।",
  "ud": "اگر کسی دوست نے آپ کو تجویز کیا ہے تو ان کا تجویزی لنک کھولیں — وہ آپ کو بکنگ فارم تک لے جائے گا جہاں کوڈ پہلے سے بھرا ہوگا، اور آپ کی پہلی بکنگ پر 5% رعایت ملے گی", "zh": "如果朋友推荐了您，请打开他们的推荐链接——它会带您到已填好代码的预订表格，您的首次预订可享受5%折扣。", "de": "Wenn ein Freund Sie empfohlen hat, öffnen Sie seinen Empfehlungslink — er führt Sie zum Buchungsformular mit bereits eingetragenem Code, und Ihre erste Buchung erhält 5 % Rabatt.", "it": "Se un amico ti ha segnalato, apri il suo link di referral — ti porta al modulo di prenotazione con il codice già inserito e la tua prima prenotazione ottiene il 5% di sconto.",
  "ru": "Если вас пригласил друг, откройте его реферальную ссылку — она приведёт вас к форме бронирования с уже введённым кодом, и ваша первая поездка будет со скидкой 5%.", "tr": "Bir arkadaşınız sizi tavsiye ettiyse referans bağlantısını açın — sizi kodu zaten doldurulmuş rezervasyon formuna götürür ve ilk rezervasyonunuzda %5 indirim alırsınız.", "ko": "친구가 추천했다면 추천 링크를 여세요. 코드가 이미 입력된 예약 양식으로 이동하며 첫 예약 시 5% 할인을 받습니다.", "ja": "友人に紹介された場合は、紹介リンクを開いてください。コードがすでに入力された予約フォームに移動し、初回予約が5%割引になります。",
  "vi": "Nếu một người bạn giới thiệu bạn, hãy mở liên kết giới thiệu của họ — nó sẽ đưa bạn đến biểu mẫu đặt xe với mã đã được điền sẵn và chuyến đặt xe đầu tiên của bạn được giảm 5%.", "fa": "اگر دوستی شما را معرفی کرده است، پیوند معرفی او را باز کنید — شما را به فرم رزرو می‌برد با کد از پیش پرشده، و اولین رزرو شما ۵٪ تخفیف می‌گیرد", "th": "หากเพื่อนแนะนำคุณ ให้เปิดลิงก์แนะนำของพวกเขา — จะพาคุณไปยังแบบฟอร์มการจองพร้อมรหัสที่กรอกไว้แล้ว และการจองครั้งแรกของคุณจะได้รับส่วนลด 5%"
};

NOEL_I18N["chat.ans_book"] = {
  "en": "Enter your pickup and drop-off, date and time in the booking form above, choose your experience, and pay by card — your chauffeur is assigned right after payment.", "es": "Escribe tu recogida y destino, fecha y hora en el formulario de arriba, elige tu experiencia y paga con tarjeta: tu chófer se asigna justo después del pago.", "fr": "Saisissez votre lieu de prise en charge et votre destination, la date et l'heure dans le formulaire ci-dessus, choisissez votre expérience et payez par carte — votre chauffeur est assigné juste après le paiement.", "ar": "أدخل مكان الاستلام والوصول والتاريخ والوقت في نموذج الحجز أعلاه، واختر تجربتك، وادفع بالبطاقة — وسيتم تعيين سائقك مباشرة بعد الدفع.",
  "pt": "Informe embarque e destino, data e hora no formulário acima, escolha sua experiência e pague com cartão — seu motorista é designado logo após o pagamento.", "ur": "Upar booking form mein apna pickup aur drop-off, date aur time likhen, apna experience chunen, aur card se pay karen — payment ke foran baad aapka chauffeur assign ho jayega.", "hi": "ऊपर बुकिंग फ़ॉर्म में अपना पिकअप और ड्रॉप-ऑफ़, तारीख और समय लिखें, अपना अनुभव चुनें, और कार्ड से भुगतान करें — भुगतान के तुरंत बाद आपका शॉफ़र नियुक्त हो जाएगा।", "bn": "উপরের বুকিং ফর্মে আপনার পিকআপ ও ড্রপ-অফ, তারিখ ও সময় লিখুন, আপনার অভিজ্ঞতা বেছে নিন, এবং কার্ডে পেমেন্ট করুন — পেমেন্টের পরপরই আপনার শোফার নিয়োগ করা হবে।",
  "ud": "اوپر والے بکنگ فارم میں پک اپ اور ڈراپ آف کے پتے، تاریخ اور وقت درج کریں، اپنا تجربہ منتخب کریں اور کارڈ سے ادائیگی کریں — ادائیگی کے فوراً بعد آپ کا ڈرائیور مقرر ہو جائے گا", "zh": "请在上方预订表格中输入上车和下车地址、日期和时间，选择您的体验并用卡支付——付款后将立即为您指派司机。", "de": "Geben Sie Abhol- und Zielort, Datum und Uhrzeit in das Buchungsformular oben ein, wählen Sie Ihr Erlebnis und bezahlen Sie per Karte — Ihr Chauffeur wird direkt nach der Zahlung zugewiesen.", "it": "Inserisci il luogo di partenza e di destinazione, data e ora nel modulo di prenotazione sopra, scegli la tua esperienza e paga con carta — il tuo chauffeur verrà assegnato subito dopo il pagamento.",
  "ru": "Введите адрес отправления и назначения, дату и время в форму бронирования выше, выберите класс и оплатите картой — шофёр будет назначен сразу после оплаты.", "tr": "Yukarıdaki rezervasyon formuna biniş ve varış adresinizi, tarih ve saati girin, deneyiminizi seçin ve kartla ödeyin — şoförünüz ödemeden hemen sonra atanır.", "ko": "위의 예약 양식에 출발지와 목적지, 날짜와 시간을 입력하고 원하는 경험을 선택한 뒤 카드로 결제하세요. 결제 후 바로 쇼퍼가 배정됩니다.", "ja": "上記の予約フォームに出発地と目的地、日付と時刻を入力し、エクスペリエンスを選択してカードでお支払いください。お支払い後すぐにショファーが割り当てられます。",
  "vi": "Nhập địa chỉ đón và trả khách, ngày và giờ vào biểu mẫu đặt xe ở trên, chọn trải nghiệm của bạn và thanh toán bằng thẻ — tài xế của bạn sẽ được chỉ định ngay sau khi thanh toán.", "fa": "در فرم رزرو بالا، نشانی‌های مبدا و مقصد، تاریخ و زمان را وارد کنید، تجربهٔ خود را انتخاب کنید و با کارت پرداخت کنید — رانندهٔ شما بلافاصله پس از پرداخت تعیین می‌شود", "th": "ป้อนที่อยู่ต้นทางและปลายทาง วันที่และเวลาในแบบฟอร์มการจองด้านบน เลือกประสบการณ์ของคุณและชำระเงินด้วยบัตร — คนขับของคุณจะได้รับมอบหมายทันทีหลังชำระเงิน"
};

NOEL_I18N["chat.ans_hello"] = {
  "en": "Hello, and welcome to Noel Chauffer. Bookings are open — enter your pickup and drop-off in the booking form to see your fare. I can still help with prices, cancellation, waiting time, lost items, or a problem with a ride.", "es": "Hola, bienvenido a Noel Chauffer. Las reservas están abiertas: escribe tu recogida y destino en el formulario para ver tu tarifa. También puedo ayudarte con precios, cancelación, tiempo de espera, objetos perdidos o un problema con un viaje.", "fr": "Bonjour et bienvenue chez Noel Chauffer. Les réservations sont ouvertes — saisissez votre lieu de prise en charge et votre destination dans le formulaire pour voir votre tarif. Je peux aussi vous aider avec les prix, l'annulation, le temps d'attente, les objets perdus ou un problème avec un trajet.", "ar": "مرحبًا بك في نويل شوفير. الحجوزات مفتوحة — أدخل مكان الاستلام والوصول في نموذج الحجز لترى أجرتك. ويمكنني أيضًا مساعدتك في الأسعار أو الإلغاء أو وقت الانتظار أو الأغراض المفقودة أو مشكلة في رحلة.",
  "pt": "Olá, bem-vindo à Noel Chauffer. As reservas estão abertas — informe embarque e destino no formulário para ver sua tarifa. Também posso ajudar com preços, cancelamento, tempo de espera, objetos perdidos ou um problema com uma viagem.", "ur": "Hello, Noel Chauffer mein welcome. Bookings khuli hain — apna pickup aur drop-off booking form mein likhen to fare dikhega. Main prices, cancellation, waiting time, lost items, ya ride ki kisi problem mein bhi madad kar sakta hoon.", "hi": "नमस्ते, नोएल शॉफ़र में स्वागत है। बुकिंग खुली है — अपना किराया देखने के लिए बुकिंग फ़ॉर्म में पिकअप और ड्रॉप-ऑफ़ लिखें। मैं कीमतों, रद्दीकरण, प्रतीक्षा समय, खोए सामान, या सवारी की किसी समस्या में भी मदद कर सकता हूँ।", "bn": "হ্যালো, নোয়েল শোফারে স্বাগতম। বুকিং খোলা আছে — ভাড়া দেখতে বুকিং ফর্মে আপনার পিকআপ ও ড্রপ-অফ লিখুন। আমি দাম, বাতিল, অপেক্ষার সময়, হারানো জিনিস, বা রাইডের কোনো সমস্যায়ও সাহায্য করতে পারি।",
  "ud": "ہیلو، Noel Chauffer میں خوش آمدید۔ بکنگ کھلی ہوئی ہے — اپنا کرایہ دیکھنے کے لیے بکنگ فارم میں پک اپ اور ڈراپ آف کے پتے درج کریں۔ میں قیمت، منسوخی، انتظار کے وقت، گمشدہ چیزوں، یا سواری کے کسی مسئلے میں بھی مدد کر سکتا ہوں", "zh": "您好，欢迎来到 Noel Chauffer。预订已开放——请在预订表格中输入上车和下车地址以查看价格。我还可以帮助您了解价格、取消、等候时间、遗失物品或行程问题。", "de": "Hallo und willkommen bei Noel Chauffer. Buchungen sind geöffnet — geben Sie Abhol- und Zielort in das Buchungsformular ein, um Ihren Preis zu sehen. Ich kann Ihnen weiterhin bei Preisen, Stornierung, Wartezeit, verlorenen Gegenständen oder einem Problem mit einer Fahrt helfen.", "it": "Ciao e benvenuto da Noel Chauffer. Le prenotazioni sono aperte — inserisci il luogo di partenza e di destinazione nel modulo di prenotazione per vedere la tua tariffa. Posso comunque aiutarti con prezzi, cancellazioni, tempi di attesa, oggetti smarriti o un problema con una corsa.",
  "ru": "Здравствуйте, добро пожаловать в Noel Chauffer. Бронирование открыто — введите адрес отправления и назначения в форму бронирования, чтобы увидеть тариф. Я также могу помочь с ценами, отменой, временем ожидания, потерянными вещами или проблемой с поездкой.", "tr": "Merhaba, Noel Chauffer'a hoş geldiniz. Rezervasyonlar açık — ücretinizi görmek için biniş ve varış adresinizi rezervasyon formuna girin. Fiyatlar, iptal, bekleme süresi, kayıp eşyalar veya bir yolculukla ilgili bir sorun konusunda yine de yardımcı olabilirim.", "ko": "안녕하세요, Noel Chauffer에 오신 것을 환영합니다. 예약이 가능합니다. 요금을 보려면 예약 양식에 출발지와 목적지를 입력하세요. 가격, 취소, 대기 시간, 분실물 또는 이동 문제에 대해서도 도와드릴 수 있습니다.", "ja": "こんにちは、Noel Chaufferへようこそ。予約は受付中です。料金を見るには予約フォームに出発地と目的地を入力してください。料金、キャンセル、待ち時間、紛失物、乗車の問題についてもお手伝いできます。",
  "vi": "Xin chào, chào mừng bạn đến với Noel Chauffer. Đặt xe đang mở — nhập địa chỉ đón và trả khách vào biểu mẫu đặt xe để xem giá. Tôi vẫn có thể giúp bạn về giá, hủy xe, thời gian chờ, đồ thất lạc hoặc vấn đề với chuyến đi.", "fa": "سلام، به Noel Chauffer خوش آمدید. رزرو باز است — برای مشاهدهٔ کرایه، نشانی‌های مبدا و مقصد را در فرم رزرو وارد کنید. همچنین می‌توانم دربارهٔ قیمت، لغو، زمان انتظار، وسایل گمشده یا هر مشکلی در سفر کمک کنم", "th": "สวัสดี ยินดีต้อนรับสู่ Noel Chauffer การจองเปิดอยู่ — ป้อนที่อยู่ต้นทางและปลายทางในแบบฟอร์มการจองเพื่อดูค่าโดยสาร ฉันยังช่วยเรื่องราคา การยกเลิก เวลารอ ของหาย หรือปัญหาเกี่ยวกับการเดินทางได้"
};

NOEL_I18N["chat.ans_human"] = {
  "en": "You are chatting with the Noel Chauffer team here. The team replies within 24 hours. If your matter is urgent, please describe it here and we will escalate it to the owner.", "es": "Estás chateando aquí con el equipo de Noel Chauffer. El equipo responde en un plazo de 24 horas. Si tu asunto es urgente, descríbelo aquí y lo escalaremos al propietario.", "fr": "Vous discutez ici avec l'équipe Noel Chauffer. L'équipe répond sous 24 heures. Si votre demande est urgente, décrivez-la ici et nous la transmettrons au propriétaire.", "ar": "أنت تتحدث هنا مع فريق نويل شوفير. يرد الفريق خلال 24 ساعة. إذا كان أمرك عاجلًا، فصِفه هنا وسنصعّده إلى المالك.",
  "pt": "Você está conversando aqui com a equipe da Noel Chauffer. A equipe responde em até 24 horas. Se o assunto for urgente, descreva-o aqui e vamos escalar para o proprietário.", "ur": "Aap yahan Noel Chauffer team se chat kar rahe hain. Team 24 hours ke andar reply karti hai. Agar aapka kaam urgent hai to yahin likhen, hum owner tak pahuncha denge.", "hi": "आप यहाँ नोएल शॉफ़र टीम से चैट कर रहे हैं। टीम 24 घंटों के भीतर जवाब देती है। यदि आपका मामला ज़रूरी है, तो कृपया इसे यहाँ बताएँ और हम इसे मालिक तक पहुँचाएँगे।", "bn": "আপনি এখানে নোয়েল শোফার টিমের সঙ্গে চ্যাট করছেন। টিম ২৪ ঘণ্টার মধ্যে উত্তর দেয়। বিষয়টি জরুরি হলে এখানে বর্ণনা করুন, আমরা মালিকের কাছে পাঠাব।",
  "ud": "آپ Noel Chauffer ٹیم سے چیٹ کر رہے ہیں۔ ٹیم 24 گھنٹوں کے اندر جواب دیتی ہے۔ اگر آپ کا معاملہ فوری ہے تو براہ کرم یہاں تفصیل بتائیں اور ہم اسے مالک تک پہنچا دیں گے", "zh": "您正在与 Noel Chauffer 团队聊天。团队会在24小时内回复。如果您的事情紧急，请在此说明，我们将上报给负责人。", "de": "Sie chatten hier mit dem Team von Noel Chauffer. Das Team antwortet innerhalb von 24 Stunden. Wenn Ihr Anliegen dringend ist, beschreiben Sie es bitte hier und wir leiten es an den Inhaber weiter.", "it": "Stai chattando con il team di Noel Chauffer. Il team risponde entro 24 ore. Se la questione è urgente, descrivila qui e la inoltreremo al proprietario.",
  "ru": "Вы общаетесь с командой Noel Chauffer. Команда отвечает в течение 24 часов. Если ваш вопрос срочный, опишите его здесь, и мы передадим его владельцу.", "tr": "Burada Noel Chauffer ekibiyle sohbet ediyorsunuz. Ekip 24 saat içinde yanıt verir. Konunuz acilse lütfen burada açıklayın, sahibine iletelim.", "ko": "Noel Chauffer 팀과 채팅하고 계십니다. 팀은 24시간 이내에 답변합니다. 급한 사안이면 여기에 설명해 주시면 소유자에게 전달하겠습니다.", "ja": "こちらはNoel Chaufferチームとのチャットです。チームは24時間以内に返信します。お急ぎの場合は、こちらに内容を記載してください。オーナーにエスカレーションします。",
  "vi": "Bạn đang trò chuyện với đội ngũ Noel Chauffer. Đội ngũ trả lời trong vòng 24 giờ. Nếu vấn đề của bạn khẩn cấp, vui lòng mô tả tại đây và chúng tôi sẽ chuyển lên cho chủ sở hữu.", "fa": "شما با تیم Noel Chauffer چت می‌کنید. تیم ظرف ۲۴ ساعت پاسخ می‌دهد. اگر موضوع شما فوری است، لطفاً اینجا توضیح دهید و ما آن را به مالک ارجاع می‌دهیم", "th": "คุณกำลังแชทกับทีม Noel Chauffer ทีมตอบกลับภายใน 24 ชั่วโมง หากเรื่องของคุณเร่งด่วน โปรดอธิบายที่นี่และเราจะส่งต่อให้เจ้าของ"
};

NOEL_I18N["chat.ans_default"] = {
  "en": "Happy to help. Bookings are open. I can answer questions about prices, cancellation, waiting time, your chauffeur's details, cars, return trips, by-the-hour rides, or lost items — just ask.", "es": "Encantado de ayudar. Las reservas están abiertas. Puedo responder preguntas sobre precios, cancelación, tiempo de espera, los datos de tu chófer, coches, viajes de regreso, viajes por horas u objetos perdidos: solo pregunta.", "fr": "Avec plaisir. Les réservations sont ouvertes. Je peux répondre à vos questions sur les prix, l'annulation, le temps d'attente, les coordonnées de votre chauffeur, les voitures, les trajets retour, les trajets à l'heure ou les objets perdus — demandez simplement.", "ar": "يسعدني المساعدة. الحجوزات مفتوحة. يمكنني الإجابة عن أسئلة حول الأسعار أو الإلغاء أو وقت الانتظار أو بيانات سائقك أو السيارات أو رحلات العودة أو الرحلات بالساعة أو الأغراض المفقودة — فقط اسأل.",
  "pt": "Prazer em ajudar. As reservas estão abertas. Posso responder perguntas sobre preços, cancelamento, tempo de espera, dados do seu motorista, carros, viagens de volta, viagens por hora ou objetos perdidos — é só perguntar.", "ur": "Madad karke khushi hogi. Bookings khuli hain. Main prices, cancellation, waiting time, aapke chauffeur ki details, gaadiyan, return trips, by-the-hour rides, ya lost items ke baare mein jawab de sakta hoon — bas poochhen.", "hi": "मदद करके खुशी होगी। बुकिंग खुली है। मैं कीमतों, रद्दीकरण, प्रतीक्षा समय, आपके शॉफ़र के विवरण, गाड़ियों, वापसी यात्राओं, घंटे के हिसाब से सवारी, या खोए सामान के बारे में जवाब दे सकता हूँ — बस पूछें।", "bn": "সাহায্য করতে পেরে খুশি। বুকিং খোলা আছে। আমি দাম, বাতিল, অপেক্ষার সময়, আপনার শোফারের বিবরণ, গাড়ি, ফেরার যাত্রা, ঘণ্টা হিসেবে রাইড, বা হারানো জিনিস সম্পর্কে উত্তর দিতে পারি — শুধু জিজ্ঞেস করুন।",
  "ud": "خوشی سے مدد کروں گا۔ بکنگ کھلی ہوئی ہے۔ میں قیمت، منسوخی، انتظار کے وقت، آپ کے ڈرائیور کی تفصیلات، گاڑیاں، واپسی کی سواری، گھنٹوں کے حساب سے کرایہ، یا گمشدہ چیزوں کے بارے میں جواب دے سکتا ہوں — بس پوچھیں", "zh": "乐意效劳。预订已开放。我可以回答关于价格、取消、等候时间、您的司机信息、车辆、返程、按小时行程或遗失物品的问题——请直接提问。", "de": "Gerne behilflich. Buchungen sind geöffnet. Ich kann Fragen zu Preisen, Stornierung, Wartezeit, den Daten Ihres Chauffeurs, Autos, Rückfahrten, stundenweisen Fahrten oder verlorenen Gegenständen beantworten — fragen Sie einfach.", "it": "Volentieri. Le prenotazioni sono aperte. Posso rispondere a domande su prezzi, cancellazioni, tempi di attesa, i dati del tuo chauffeur, auto, viaggi di ritorno, corse a ore o oggetti smarriti — chiedi pure.",
  "ru": "Рад помочь. Бронирование открыто. Я могу ответить на вопросы о ценах, отмене, времени ожидания, данных вашего шофёра, автомобилях, обратных поездках, почасовых поездках или потерянных вещах — просто спросите.", "tr": "Memnuniyetle yardımcı olurum. Rezervasyonlar açık. Fiyatlar, iptal, bekleme süresi, şoförünüzün bilgileri, araçlar, dönüş yolculukları, saatlik yolculuklar veya kayıp eşyalar hakkında sorularınızı yanıtlayabilirim — sorunuz yeterli.", "ko": "기꺼이 도와드리겠습니다. 예약이 가능합니다. 가격, 취소, 대기 시간, 쇼퍼 정보, 차량, 귀환 여정, 시간제 이동, 분실물에 대해 답변해 드릴 수 있습니다. 무엇이든 물어보세요.", "ja": "喜んでお手伝いします。予約は受付中です。料金、キャンセル、待ち時間、ショファーの詳細、車両、帰りの乗車、時間貸し、紛失物についてお答えできます。どうぞお尋ねください。",
  "vi": "Rất sẵn lòng giúp đỡ. Đặt xe đang mở. Tôi có thể trả lời các câu hỏi về giá, hủy xe, thời gian chờ, thông tin tài xế của bạn, xe cộ, chuyến về, chuyến đi theo giờ hoặc đồ thất lạc — cứ hỏi nhé.", "fa": "با کمال میل کمک می‌کنم. رزرو باز است. می‌توانم دربارهٔ قیمت، لغو، زمان انتظار، جزئیات رانندهٔ شما، خودروها، سفر برگشت، کرایهٔ ساعتی یا وسایل گمشده پاسخ دهم — فقط بپرسید", "th": "ยินดีช่วยเหลือ การจองเปิดอยู่ ฉันตอบคำถามเกี่ยวกับราคา การยกเลิก เวลารอ รายละเอียดคนขับของคุณ รถยนต์ เที่ยวกลับ การเดินทางรายชั่วโมง หรือของหายได้ — ถามได้เลย"
};

NOEL_I18N["chat.placeholder"] = {
  "en": "Type your message…", "es": "Escribe tu mensaje…", "fr": "Écrivez votre message…", "ar": "اكتب رسالتك…",
  "pt": "Digite sua mensagem…", "ur": "Apna message likhen…", "hi": "अपना संदेश लिखें…", "bn": "আপনার বার্তা লিখুন…",
  "ud": "اپنا پیغام لکھیں…", "zh": "输入您的消息…", "de": "Geben Sie Ihre Nachricht ein…", "it": "Scrivi il tuo messaggio…",
  "ru": "Введите ваше сообщение…", "tr": "Mesajınızı yazın…", "ko": "메시지를 입력하세요…", "ja": "メッセージを入力…",
  "vi": "Nhập tin nhắn của bạn…", "fa": "پیام خود را بنویسید…", "th": "พิมพ์ข้อความของคุณ…"
};

NOEL_I18N["chat.send"] = {
  "en": "Send", "es": "Enviar", "fr": "Envoyer", "ar": "إرسال",
  "pt": "Enviar", "ur": "Send", "hi": "भेजें", "bn": "পাঠান",
  "ud": "بھیجیں", "zh": "发送", "de": "Senden", "it": "Invia",
  "ru": "Отправить", "tr": "Gönder", "ko": "보내기", "ja": "送信",
  "vi": "Gửi", "fa": "ارسال", "th": "ส่ง"
};

NOEL_I18N["chat.book_ride"] = {
  "en": "Book a ride", "es": "Reservar un viaje", "fr": "Réserver un trajet", "ar": "احجز رحلة",
  "pt": "Reservar uma viagem", "ur": "Ride book karen", "hi": "सवारी बुक करें", "bn": "রাইড বুক করুন",
  "ud": "سواری بک کریں", "zh": "预订行程", "de": "Fahrt buchen", "it": "Prenota una corsa",
  "ru": "Забронировать поездку", "tr": "Yolculuk rezerve et", "ko": "이동 예약", "ja": "乗車を予約する",
  "vi": "Đặt chuyến đi", "fa": "رزرو سفر", "th": "จองการเดินทาง"
};

NOEL_I18N["chat.hours"] = {
  "en": "Our hours", "es": "Nuestro horario", "fr": "Nos horaires", "ar": "ساعات عملنا",
  "pt": "Nosso horário", "ur": "Hamare hours", "hi": "हमारा समय", "bn": "আমাদের সময়",
  "ud": "ہمارے اوقات", "zh": "我们的营业时间", "de": "Unsere Öffnungszeiten", "it": "I nostri orari",
  "ru": "Наши часы работы", "tr": "Çalışma saatlerimiz", "ko": "운영 시간", "ja": "営業時間",
  "vi": "Giờ làm việc của chúng tôi", "fa": "ساعت‌های کاری ما", "th": "เวลาทำการของเรา"
};

NOEL_I18N["chat.service_area"] = {
  "en": "Service area", "es": "Zona de servicio", "fr": "Zone de service", "ar": "منطقة الخدمة",
  "pt": "Área de atendimento", "ur": "Service area", "hi": "सेवा क्षेत्र", "bn": "পরিষেবা এলাকা",
  "ud": "سروس کا علاقہ", "zh": "服务区域", "de": "Servicegebiet", "it": "Area di servizio",
  "ru": "Зона обслуживания", "tr": "Hizmet bölgesi", "ko": "서비스 지역", "ja": "サービスエリア",
  "vi": "Khu vực phục vụ", "fa": "منطقهٔ خدمات", "th": "พื้นที่ให้บริการ"
};

NOEL_I18N["chat.contact"] = {
  "en": "Contact us", "es": "Contáctanos", "fr": "Contactez-nous", "ar": "اتصل بنا",
  "pt": "Fale conosco", "ur": "Hum se rabta karen", "hi": "हमसे संपर्क करें", "bn": "আমাদের সঙ্গে যোগাযোগ করুন",
  "ud": "ہم سے رابطہ کریں", "zh": "联系我们", "de": "Kontakt", "it": "Contattaci",
  "ru": "Связаться с нами", "tr": "Bize ulaşın", "ko": "문의하기", "ja": "お問い合わせ",
  "vi": "Liên hệ chúng tôi", "fa": "تماس با ما", "th": "ติดต่อเรา"
};

NOEL_I18N["chat.more_options"] = {
  "en": "More options", "es": "Más opciones", "fr": "Plus d'options", "ar": "خيارات أخرى",
  "pt": "Mais opções", "ur": "Aur options", "hi": "और विकल्प", "bn": "আরও বিকল্প",
  "ud": "مزید اختیارات", "zh": "更多选项", "de": "Weitere Optionen", "it": "Altre opzioni",
  "ru": "Другие варианты", "tr": "Diğer seçenekler", "ko": "추가 옵션", "ja": "その他のオプション",
  "vi": "Thêm lựa chọn", "fa": "گزینه‌های بیشتر", "th": "ตัวเลือกเพิ่มเติม"
};

NOEL_I18N["chat.new_message"] = {
  "en": "New message", "es": "Nuevo mensaje", "fr": "Nouveau message", "ar": "رسالة جديدة",
  "pt": "Nova mensagem", "ur": "Naya message", "hi": "नया संदेश", "bn": "নতুন বার্তা",
  "ud": "نیا پیغام", "zh": "新消息", "de": "Neue Nachricht", "it": "Nuovo messaggio",
  "ru": "Новое сообщение", "tr": "Yeni mesaj", "ko": "새 메시지", "ja": "新しいメッセージ",
  "vi": "Tin nhắn mới", "fa": "پیام جدید", "th": "ข้อความใหม่"
};

NOEL_I18N["hourly.title"] = {
  "en": "Hourly hire", "es": "Alquiler por horas", "fr": "Location à l'heure", "ar": "الحجز بالساعة",
  "pt": "Aluguel por hora", "ur": "Hourly hire", "hi": "घंटे के हिसाब से किराया", "bn": "ঘণ্টা হিসেবে ভাড়া",
  "ud": "فی گھنٹہ کرایہ", "zh": "按小时租用", "de": "Stundenweise Miete", "it": "Noleggio a ore",
  "ru": "Почасовая аренда", "tr": "Saatlik kiralama", "ko": "시간제 대여", "ja": "時間貸し",
  "vi": "Thuê theo giờ", "fa": "کرایهٔ ساعتی", "th": "เช่ารายชั่วโมง"
};

NOEL_I18N["hourly.hours"] = {
  "en": "Hours", "es": "Horas", "fr": "Heures", "ar": "الساعات",
  "pt": "Horas", "ur": "Hours", "hi": "घंटे", "bn": "ঘণ্টা",
  "ud": "گھنٹے", "zh": "小时", "de": "Stunden", "it": "Ore",
  "ru": "Часы", "tr": "Saat", "ko": "시간", "ja": "時間",
  "vi": "Giờ", "fa": "ساعت", "th": "ชั่วโมง"
};

NOEL_I18N["hourly.per_hour"] = {
  "en": "/hr", "es": "/h", "fr": "/h", "ar": "/ساعة",
  "pt": "/h", "ur": "/hr", "hi": "/घंटा", "bn": "/ঘণ্টা",
  "ud": "/فی گھنٹہ", "zh": "/小时", "de": "/Std.", "it": "/ora",
  "ru": "/час", "tr": "/sa", "ko": "/시간", "ja": "/時間",
  "vi": "/giờ", "fa": "/ساعت", "th": "/ชั่วโมง"
};

NOEL_I18N["hourly.miles_included"] = {
  "en": "{n} miles included per hour", "es": "{n} millas incluidas por hora", "fr": "{n} miles inclus par heure", "ar": "{n} ميل مشمول في الساعة",
  "pt": "{n} milhas incluídas por hora", "ur": "{n} miles per hour shamil hain", "hi": "प्रति घंटे {n} मील शामिल हैं", "bn": "প্রতি ঘণ্টায় {n} মাইল অন্তর্ভুক্ত",
  "ud": "فی گھنٹہ {n} میل شامل ہیں", "zh": "每小时包含 {n} 英里", "de": "{n} Meilen pro Stunde inklusive", "it": "{n} miglia incluse all'ora",
  "ru": "{n} миль включено в час", "tr": "Saat başına {n} mil dahildir", "ko": "시간당 {n}마일 포함", "ja": "1時間あたり{n}マイルを含む",
  "vi": "Bao gồm {n} dặm mỗi giờ", "fa": "{n} مایل در هر ساعت شامل است", "th": "รวม {n} ไมล์ต่อชั่วโมง"
};

NOEL_I18N["hourly.min_2"] = {
  "en": "Minimum 2 hours", "es": "Mínimo 2 horas", "fr": "Minimum 2 heures", "ar": "الحد الأدنى ساعتان",
  "pt": "Mínimo de 2 horas", "ur": "Minimum 2 hours", "hi": "न्यूनतम 2 घंटे", "bn": "সর্বনিম্ন ২ ঘণ্টা",
  "ud": "کم از کم 2 گھنٹے", "zh": "最少2小时", "de": "Mindestens 2 Stunden", "it": "Minimo 2 ore",
  "ru": "Минимум 2 часа", "tr": "En az 2 saat", "ko": "최소 2시간", "ja": "最低2時間",
  "vi": "Tối thiểu 2 giờ", "fa": "حداقل ۲ ساعت", "th": "ขั้นต่ำ 2 ชั่วโมง"
};

NOEL_I18N["chat.q_book"] = {
  "en": "How do I book?", "es": "¿Cómo reservo?", "fr": "Comment réserver ?", "ar": "كيف أحجز؟",
  "pt": "Como reservo?", "ur": "Ride kaise book karen?", "hi": "मैं सवारी कैसे बुक करूँ?", "bn": "আমি কীভাবে রাইড বুক করব?",
  "ud": "کیسے بک کریں؟", "zh": "如何预订？", "de": "Wie buche ich?", "it": "Come prenoto?",
  "ru": "Как забронировать?", "tr": "Nasıl rezervasyon yaparım?", "ko": "예약은 어떻게 하나요?", "ja": "予約方法は？",
  "vi": "Tôi đặt xe như thế nào?", "fa": "چگونه رزرو کنم؟", "th": "จองอย่างไร?"
};

NOEL_I18N["chat.q_paused"] = {
  "en": "Are bookings paused?", "es": "¿Las reservas están en pausa?", "fr": "Les réservations sont-elles en pause ?", "ar": "هل الحجوزات متوقفة مؤقتًا؟",
  "pt": "As reservas estão pausadas?", "ur": "Kya bookings paused hain?", "hi": "क्या बुकिंग रुकी हुई हैं?", "bn": "বুকিং কি বন্ধ আছে?",
  "ud": "کیا بکنگ رکی ہوئی ہے؟", "zh": "预订暂停了吗？", "de": "Sind Buchungen pausiert?", "it": "Le prenotazioni sono in pausa?",
  "ru": "Бронирование приостановлено?", "tr": "Rezervasyonlar duraklatıldı mı?", "ko": "예약이 중단되었나요?", "ja": "予約は一時停止中ですか？",
  "vi": "Đặt xe có bị tạm dừng không?", "fa": "آیا رزرو متوقف شده است؟", "th": "การจองหยุดชั่วคราวหรือไม่?"
};

NOEL_I18N["chat.q_cancel"] = {
  "en": "Cancellation rules", "es": "Reglas de cancelación", "fr": "Règles d'annulation", "ar": "قواعد الإلغاء",
  "pt": "Regras de cancelamento", "ur": "Cancellation rules", "hi": "रद्दीकरण के नियम", "bn": "বাতিলের নিয়ম",
  "ud": "منسوخی کے اصول", "zh": "取消规则", "de": "Stornierungsbedingungen", "it": "Regole di cancellazione",
  "ru": "Правила отмены", "tr": "İptal kuralları", "ko": "취소 규정", "ja": "キャンセル規定",
  "vi": "Quy định hủy xe", "fa": "قوانین لغو", "th": "กฎการยกเลิก"
};

NOEL_I18N["chat.q_waiting"] = {
  "en": "Waiting time", "es": "Tiempo de espera", "fr": "Temps d'attente", "ar": "وقت الانتظار",
  "pt": "Tempo de espera", "ur": "Waiting time", "hi": "प्रतीक्षा समय", "bn": "অপেক্ষার সময়",
  "ud": "انتظار کا وقت", "zh": "等候时间", "de": "Wartezeit", "it": "Tempo di attesa",
  "ru": "Время ожидания", "tr": "Bekleme süresi", "ko": "대기 시간", "ja": "待ち時間",
  "vi": "Thời gian chờ", "fa": "زمان انتظار", "th": "เวลารอ"
};

NOEL_I18N["chat.q_lost"] = {
  "en": "Lost item", "es": "Objeto perdido", "fr": "Objet perdu", "ar": "غرض مفقود",
  "pt": "Item perdido", "ur": "Khoi hui cheez", "hi": "खोई हुई चीज़", "bn": "হারানো জিনিস",
  "ud": "گمشدہ چیز", "zh": "遗失物品", "de": "Verlorener Gegenstand", "it": "Oggetto smarrito",
  "ru": "Потерянная вещь", "tr": "Kayıp eşya", "ko": "분실물", "ja": "紛失物",
  "vi": "Đồ thất lạc", "fa": "وسیلهٔ گمشده", "th": "ของหาย"
};

NOEL_I18N["chat.type_message"] = {
  "en": "Type your message…", "es": "Escribe tu mensaje…", "fr": "Écrivez votre message…", "ar": "اكتب رسالتك…",
  "pt": "Digite sua mensagem…", "ur": "Apna message likhen…", "hi": "अपना संदेश लिखें…", "bn": "আপনার বার্তা লিখুন…",
  "ud": "اپنا پیغام لکھیں…", "zh": "输入您的消息…", "de": "Geben Sie Ihre Nachricht ein…", "it": "Scrivi il tuo messaggio…",
  "ru": "Введите ваше сообщение…", "tr": "Mesajınızı yazın…", "ko": "메시지를 입력하세요…", "ja": "メッセージを入力…",
  "vi": "Nhập tin nhắn của bạn…", "fa": "پیام خود را بنویسید…", "th": "พิมพ์ข้อความของคุณ…"
};

NOEL_I18N["class.back_form"] = {
  "en": "← Back to booking form", "es": "← Volver al formulario de reserva", "fr": "← Retour au formulaire de réservation", "ar": "← العودة إلى نموذج الحجز",
  "pt": "← Voltar ao formulário de reserva", "ur": "← Booking form par wapas", "hi": "← बुकिंग फ़ॉर्म पर वापस जाएँ", "bn": "← বুকিং ফর্মে ফিরে যান",
  "ud": "← بکنگ فارم پر واپس جائیں", "zh": "← 返回预订表格", "de": "← Zurück zum Buchungsformular", "it": "← Torna al modulo di prenotazione",
  "ru": "← Назад к форме бронирования", "tr": "← Rezervasyon formuna geri dön", "ko": "← 예약 양식으로 돌아가기", "ja": "← 予約フォームに戻る",
  "vi": "← Quay lại biểu mẫu đặt xe", "fa": "← بازگشت به فرم رزرو", "th": "← กลับไปที่แบบฟอร์มการจอง"
};

NOEL_I18N["class.cap_seating_note"] = {
  "en": "— please respect the seating capacity for safety.", "es": "— respete la capacidad de asientos por seguridad.", "fr": "— veuillez respecter la capacité d'assise pour votre sécurité.", "ar": "— يرجى احترام سعة المقاعد من أجل السلامة.",
  "pt": "— respeite a capacidade de assentos por segurança.", "ur": "— safety ke liye seating capacity ka khayal rakhen.", "hi": "— सुरक्षा के लिए बैठने की क्षमता का सम्मान करें।", "bn": "— নিরাপত্তার জন্য আসন ধারণক্ষমতা মেনে চলুন।",
  "ud": "— حفاظت کے لیے بیٹھنے کی گنجائش کا احترام کریں", "zh": "— 出于安全考虑，请遵守座位容量。", "de": "— bitte beachten Sie aus Sicherheitsgründen die Sitzplatzkapazität.", "it": "— per sicurezza, rispetta la capacità dei posti.",
  "ru": "— пожалуйста, соблюдайте вместимость мест из соображений безопасности.", "tr": "— güvenlik için lütfen oturma kapasitesine uyun.", "ko": "— 안전을 위해 좌석 정원을 준수해 주세요.", "ja": "— 安全のため、座席定員をお守りください。",
  "vi": "— vì lý do an toàn, vui lòng tôn trọng sức chứa ghế ngồi.", "fa": "— لطفاً برای ایمنی به ظرفیت صندلی احترام بگذارید", "th": "— โปรดเคารพความจุที่นั่งเพื่อความปลอดภัย"
};

NOEL_I18N["class.capacity_luggage"] = {
  "en": "Luggage", "es": "Equipaje", "fr": "Bagages", "ar": "الأمتعة",
  "pt": "Bagagem", "ur": "Luggage", "hi": "सामान", "bn": "লাগেজ",
  "ud": "سامان", "zh": "行李", "de": "Gepäck", "it": "Bagagli",
  "ru": "Багаж", "tr": "Bagaj", "ko": "수하물", "ja": "荷物",
  "vi": "Hành lý", "fa": "چمدان", "th": "กระเป๋า"
};

NOEL_I18N["class.capacity_seating"] = {
  "en": "Seating", "es": "Asientos", "fr": "Places assises", "ar": "المقاعد",
  "pt": "Assentos", "ur": "Seating", "hi": "बैठने की जगह", "bn": "বসার জায়গা",
  "ud": "نشستیں", "zh": "座位", "de": "Sitzplätze", "it": "Posti",
  "ru": "Места", "tr": "Oturma", "ko": "좌석", "ja": "座席",
  "vi": "Chỗ ngồi", "fa": "صندلی", "th": "ที่นั่ง"
};

NOEL_I18N["class.choose_vehicle_class"] = {
  "en": "Choose your vehicle class", "es": "Elige la clase de vehículo", "fr": "Choisissez votre catégorie de véhicule", "ar": "اختر فئة السيارة",
  "pt": "Escolha a classe do veículo", "ur": "Apni vehicle class chunen", "hi": "अपनी वाहन श्रेणी चुनें", "bn": "আপনার গাড়ির শ্রেণি বেছে নিন",
  "ud": "اپنی گاڑی کی کلاس منتخب کریں", "zh": "选择您的车辆级别", "de": "Wählen Sie Ihre Fahrzeugklasse", "it": "Scegli la classe del veicolo",
  "ru": "Выберите класс автомобиля", "tr": "Araç sınıfınızı seçin", "ko": "차량 클래스 선택", "ja": "車両クラスを選択",
  "vi": "Chọn hạng xe của bạn", "fa": "کلاس خودروی خود را انتخاب کنید", "th": "เลือกระดับรถยนต์ของคุณ"
};

NOEL_I18N["class.continue"] = {
  "en": "Continue", "es": "Continuar", "fr": "Continuer", "ar": "متابعة",
  "pt": "Continuar", "ur": "Continue", "hi": "जारी रखें", "bn": "চালিয়ে যান",
  "ud": "جاری رکھیں", "zh": "继续", "de": "Weiter", "it": "Continua",
  "ru": "Продолжить", "tr": "Devam", "ko": "계속", "ja": "続ける",
  "vi": "Tiếp tục", "fa": "ادامه", "th": "ดำเนินการต่อ"
};

NOEL_I18N["class.included_meet"] = {
  "en": "Personal meet & greet", "es": "Recibimiento personal", "fr": "Accueil personnalisé", "ar": "استقبال شخصي",
  "pt": "Recepção pessoal", "ur": "Personal meet & greet", "hi": "व्यक्तिगत स्वागत", "bn": "ব্যক্তিগত অভ্যর্থনা",
  "ud": "ذاتی استقبال", "zh": "专人迎接", "de": "Persönlicher Empfang", "it": "Accoglienza personale",
  "ru": "Личная встреча", "tr": "Kişisel karşılama", "ko": "직접 맞이 서비스", "ja": "パーソナルな出迎え",
  "vi": "Đón tiếp trực tiếp", "fa": "استقبال شخصی", "th": "ต้อนรับส่วนตัว"
};

NOEL_I18N["class.included_wait"] = {
  "en": "Includes up to 15 minutes of free wait time", "es": "Incluye hasta 15 minutos de espera gratis", "fr": "Jusqu'à 15 minutes d'attente gratuite incluses", "ar": "يشمل حتى 15 دقيقة انتظار مجاني",
  "pt": "Inclui até 15 minutos de espera gratuita", "ur": "15 minutes tak free wait time shamil hai", "hi": "15 मिनट तक का मुफ़्त प्रतीक्षा समय शामिल है", "bn": "১৫ মিনিট পর্যন্ত বিনামূল্যে অপেক্ষার সময় অন্তর্ভুক্ত",
  "ud": "15 منٹ تک مفت انتظار شامل ہے", "zh": "包含最多15分钟免费等候时间", "de": "Bis zu 15 Minuten kostenlose Wartezeit inklusive", "it": "Fino a 15 minuti di attesa gratuita inclusi",
  "ru": "До 15 минут бесплатного ожидания включено", "tr": "15 dakikaya kadar ücretsiz bekleme dahildir", "ko": "최대 15분 무료 대기 포함", "ja": "最大15分の無料待ち時間を含む",
  "vi": "Bao gồm tối đa 15 phút chờ miễn phí", "fa": "تا ۱۵ دقیقه انتظار رایگان شامل است", "th": "รวมเวลารอฟรีสูงสุด 15 นาที"
};

NOEL_I18N["class.included_cancel"] = {
  "en": "Free to cancel up to 1 hour before pickup", "es": "Cancelación gratuita hasta 1 hora antes de la recogida", "fr": "Annulation gratuite jusqu'à 1 heure avant la prise en charge", "ar": "إلغاء مجاني حتى ساعة واحدة قبل موعد الاستلام",
  "pt": "Cancelamento gratuito até 1 hora antes da coleta", "ur": "Pickup se 1 hour pehle tak free cancel", "hi": "पिकअप से 1 घंटे पहले तक मुफ़्त रद्दीकरण", "bn": "পিকআপের ১ ঘণ্টা আগে পর্যন্ত বিনামূল্যে বাতিল",
  "ud": "پک اپ سے 1 گھنٹہ پہلے تک مفت منسوخی", "zh": "上车前1小时内免费取消", "de": "Kostenlose Stornierung bis 1 Stunde vor der Abholung", "it": "Cancellazione gratuita fino a 1 ora prima del ritiro",
  "ru": "Бесплатная отмена до 1 часа до подачи", "tr": "Binişten 1 saate kadar ücretsiz iptal", "ko": "픽업 1시간 전까지 무료 취소", "ja": "乗車の1時間前まで無料キャンセル",
  "vi": "Hủy miễn phí đến 1 giờ trước giờ đón", "fa": "لغو رایگان تا ۱ ساعت پیش از سوارشدن", "th": "ยกเลิกฟรีถึง 1 ชั่วโมงก่อนเวลารับ"
};

NOEL_I18N["class.included_chargers"] = {
  "en": "iOS and Android chargers onboard", "es": "Cargadores iOS y Android a bordo", "fr": "Chargeurs iOS et Android à bord", "ar": "شواحن iOS وAndroid في السيارة",
  "pt": "Carregadores iOS e Android a bordo", "ur": "Gaari mein iOS aur Android chargers", "hi": "गाड़ी में iOS और Android चार्जर", "bn": "গাড়িতে iOS ও Android চার্জার",
  "ud": "گاڑی میں iOS اور Android چارجر", "zh": "车上配有 iOS 和 Android 充电器", "de": "iOS- und Android-Ladegeräte an Bord", "it": "Caricabatterie iOS e Android a bordo",
  "ru": "Зарядные устройства iOS и Android на борту", "tr": "Araçta iOS ve Android şarj cihazları", "ko": "차량 내 iOS 및 Android 충전기", "ja": "車内にiOSおよびAndroid充電器",
  "vi": "Bộ sạc iOS và Android trên xe", "fa": "شارژر iOS و Android در خودرو", "th": "ที่ชาร์จ iOS และ Android ในรถ"
};

NOEL_I18N["class.included_luggage"] = {
  "en": "Assistance with luggage at pickup and drop-off", "es": "Ayuda con el equipaje en la recogida y la entrega", "fr": "Aide avec les bagages à la prise en charge et à l'arrivée", "ar": "مساعدة في الأمتعة عند الاستلام والتوصيل",
  "pt": "Ajuda com a bagagem na coleta e na entrega", "ur": "Pickup aur drop-off par luggage mein madad", "hi": "पिकअप और ड्रॉप-ऑफ़ पर सामान में सहायता", "bn": "পিকআপ ও ড্রপ-অফে লাগেজে সাহায্য",
  "ud": "پک اپ اور ڈراپ آف پر سامان میں مدد", "zh": "上车和下车时协助搬运行李", "de": "Hilfe mit dem Gepäck bei Abholung und Ankunft", "it": "Assistenza con i bagagli al ritiro e alla consegna",
  "ru": "Помощь с багажом при подаче и высадке", "tr": "Biniş ve inişte bagaj yardımı", "ko": "픽업 및 하차 시 수하물 도움", "ja": "乗車時と降車時の荷物のお手伝い",
  "vi": "Hỗ trợ hành lý khi đón và trả khách", "fa": "کمک با چمدان در سوارشدن و پیاده‌شدن", "th": "ช่วยเหลือกระเป๋าเมื่อรับและส่ง"
};

NOEL_I18N["class.name"] = {
  "en": "Your name", "es": "Tu nombre", "fr": "Votre nom", "ar": "اسمك",
  "pt": "Seu nome", "ur": "Aapka naam", "hi": "आपका नाम", "bn": "আপনার নাম",
  "ud": "آپ کا نام", "zh": "您的姓名", "de": "Ihr Name", "it": "Il tuo nome",
  "ru": "Ваше имя", "tr": "Adınız", "ko": "이름", "ja": "お名前",
  "vi": "Tên của bạn", "fa": "نام شما", "th": "ชื่อของคุณ"
};

NOEL_I18N["class.name_ph"] = {
  "en": "Full name", "es": "Nombre completo", "fr": "Nom complet", "ar": "الاسم الكامل",
  "pt": "Nome completo", "ur": "Poora naam", "hi": "पूरा नाम", "bn": "পুরো নাম",
  "ud": "پورا نام", "zh": "全名", "de": "Vollständiger Name", "it": "Nome completo",
  "ru": "Полное имя", "tr": "Tam ad", "ko": "성명", "ja": "フルネーム",
  "vi": "Họ tên đầy đủ", "fa": "نام کامل", "th": "ชื่อเต็ม"
};

NOEL_I18N["class.phone_ph"] = {
  "en": "Your phone number", "es": "Tu número de teléfono", "fr": "Votre numéro de téléphone", "ar": "رقم هاتفك",
  "pt": "Seu número de telefone", "ur": "Aapka phone number", "hi": "आपका फ़ोन नंबर", "bn": "আপনার ফোন নম্বর",
  "ud": "آپ کا فون نمبر", "zh": "您的电话号码", "de": "Ihre Telefonnummer", "it": "Il tuo numero di telefono",
  "ru": "Ваш номер телефона", "tr": "Telefon numaranız", "ko": "전화번호", "ja": "お客様の電話番号",
  "vi": "Số điện thoại của bạn", "fa": "شماره تلفن شما", "th": "หมายเลขโทรศัพท์ของคุณ"
};

NOEL_I18N["class.email_ph"] = {
  "en": "you@example.com", "es": "you@example.com", "fr": "you@example.com", "ar": "you@example.com",
  "pt": "you@example.com", "ur": "you@example.com", "hi": "you@example.com", "bn": "you@example.com",
  "ud": "you@example.com", "zh": "you@example.com", "de": "you@example.com", "it": "you@example.com",
  "ru": "you@example.com", "tr": "you@example.com", "ko": "you@example.com", "ja": "you@example.com",
  "vi": "you@example.com", "fa": "you@example.com", "th": "you@example.com"
};

NOEL_I18N["class.note_capacity"] = {
  "en": "Guest and luggage capacities must be respected for safety reasons. If you are unsure, select a larger class.", "es": "Las capacidades de pasajeros y equipaje deben respetarse por seguridad. Si no está seguro, elija una clase superior.", "fr": "Les capacités passagers et bagages doivent être respectées pour des raisons de sécurité. En cas de doute, choisissez une catégorie supérieure.", "ar": "يجب احترام سعة الركاب والأمتعة لأسباب تتعلق بالسلامة. إذا كنت غير متأكد، فاختر فئة أكبر.",
  "pt": "As capacidades de passageiros e bagagem devem ser respeitadas por segurança. Se não tiver certeza, escolha uma classe maior.", "ur": "Safety ke liye guest aur luggage capacity ka khayal rakhen. Agar sure nahi hain, to badi class chunen.", "hi": "सुरक्षा कारणों से यात्री और सामान की क्षमता का सम्मान करें। यदि आप अनिश्चित हैं, तो बड़ी श्रेणी चुनें।", "bn": "নিরাপত্তার কারণে যাত্রী ও লাগেজের ধারণক্ষমতা মেনে চলতে হবে। নিশ্চিত না হলে বড় শ্রেণি বেছে নিন।",
  "ud": "حفاظت کے لیے مسافروں اور سامان کی گنجائش کا احترام کرنا ضروری ہے۔ اگر یقین نہ ہو تو بڑی کلاس منتخب کریں", "zh": "出于安全原因，必须遵守乘客和行李容量。如果不确定，请选择更大的级别。", "de": "Die Kapazitäten für Gäste und Gepäck müssen aus Sicherheitsgründen eingehalten werden. Wenn Sie unsicher sind, wählen Sie eine größere Klasse.", "it": "Le capacità di ospiti e bagagli devono essere rispettate per motivi di sicurezza. Se non sei sicuro, seleziona una classe superiore.",
  "ru": "Вместимость для гостей и багажа должна соблюдаться из соображений безопасности. Если вы не уверены, выберите класс побольше.", "tr": "Güvenlik nedeniyle yolcu ve bagaj kapasitelerine uyulmalıdır. Emin değilseniz daha büyük bir sınıf seçin.", "ko": "안전을 위해 승객 및 수하물 정원을 준수해야 합니다. 확실하지 않으면 더 큰 클래스를 선택하세요.", "ja": "安全のため、乗客と荷物の定員を守る必要があります。ご不明な場合は、より大きなクラスを選択してください。",
  "vi": "Sức chứa khách và hành lý phải được tôn trọng vì lý do an toàn. Nếu bạn không chắc, hãy chọn hạng lớn hơn.", "fa": "برای ایمنی باید به ظرفیت مسافر و چمدان احترام گذاشت. اگر مطمئن نیستید، کلاس بزرگ‌تر را انتخاب کنید", "th": "ต้องเคารพความจุผู้โดยสารและกระเป๋าเพื่อความปลอดภัย หากไม่แน่ใจ โปรดเลือกระดับที่ใหญ่กว่า"
};

NOEL_I18N["class.note_fare"] = {
  "en": "Your estimated total fare is based on the trip details shown above. The final fare may change if you change the pickup or drop-off location, change the vehicle type, or a different route is taken.", "es": "La tarifa total estimada se basa en los detalles del viaje indicados arriba. La tarifa final puede cambiar si cambia el lugar de recogida o entrega, el tipo de vehículo o si se toma otra ruta.", "fr": "Le tarif total estimé est basé sur les détails du trajet ci-dessus. Le tarif final peut changer si vous modifiez le lieu de prise en charge ou de dépôt, le type de véhicule ou si un autre itinéraire est suivi.", "ar": "الأجرة الإجمالية التقديرية مبنية على تفاصيل الرحلة أعلاه. قد تتغير الأجرة النهائية إذا غيّرت مكان الاستلام أو التوصيل أو نوع السيارة أو تم اتخاذ طريق مختلف.",
  "pt": "A tarifa total estimada baseia-se nos detalhes da viagem acima. A tarifa final pode mudar se você alterar o local de coleta ou entrega, o tipo de veículo ou se outra rota for seguida.", "ur": "Aapki estimated total fare upar dikhaye gaye trip details par hai. Final fare badal sakta hai agar aap pickup ya drop-off jagah, vehicle type badlen, ya koi doosra route liya jaye.", "hi": "आपकी अनुमानित कुल किराया ऊपर दिखाए गए यात्रा विवरण पर आधारित है। अंतिम किराया बदल सकता है यदि आप पिकअप या ड्रॉप-ऑफ़ स्थान, वाहन का प्रकार बदलते हैं, या कोई अलग मार्ग लिया जाता है।", "bn": "আপনার আনুমানিক মোট ভাড়া উপরে দেখানো ট্রিপের বিবরণের উপর ভিত্তি করে। পিকআপ বা ড্রপ-অফের জায়গা, গাড়ির ধরন বদলালে বা অন্য রুট নিলে চূড়ান্ত ভাড়া বদলাতে পারে।",
  "ud": "آپ کا تخمینی کل کرایہ اوپر دکھائی گئی سواری کی تفصیل پر مبنی ہے۔ اگر آپ پک اپ یا ڈراپ آف کی جگہ تبدیل کریں، گاڑی کی قسم بدلیں، یا مختلف راستہ استعمال کریں تو حتمی کرایہ تبدیل ہو سکتا ہے", "zh": "您的预估总费用基于上方显示的行程详情。如果您更改上车或下车地点、更改车辆类型或采取不同路线，最终费用可能会发生变化。", "de": "Ihr geschätzter Gesamtpreis basiert auf den oben angegebenen Reisedetails. Der endgültige Preis kann sich ändern, wenn Sie den Abhol- oder Zielort ändern, den Fahrzeugtyp wechseln oder eine andere Route genommen wird.", "it": "La tariffa totale stimata si basa sui dettagli del viaggio mostrati sopra. La tariffa finale può cambiare se modifichi il luogo di partenza o di destinazione, il tipo di veicolo o se viene preso un percorso diverso.",
  "ru": "Ваша предполагаемая общая стоимость рассчитана на основе данных поездки, указанных выше. Итоговая стоимость может измениться, если вы измените адрес отправления или назначения, тип автомобиля или будет выбран другой маршрут.", "tr": "Tahmini toplam ücretiniz yukarıda gösterilen yolculuk ayrıntılarına dayanmaktadır. Biniş veya varış yerini değiştirirseniz, araç türünü değiştirirseniz veya farklı bir rota izlenirse nihai ücret değişebilir.", "ko": "예상 총 요금은 위에 표시된 이동 정보를 기준으로 합니다. 출발지나 목적지를 변경하거나 차량 종류를 바꾸거나 다른 경로를 이용하면 최종 요금이 달라질 수 있습니다.", "ja": "推定合計料金は、上記に表示された乗車詳細に基づきます。出発地または目的地を変更したり、車両タイプを変更したり、別のルートを取ったりすると、最終料金が変わる場合があります。",
  "vi": "Tổng giá ước tính của bạn dựa trên chi tiết chuyến đi hiển thị ở trên. Giá cuối cùng có thể thay đổi nếu bạn thay đổi địa điểm đón hoặc trả khách, thay đổi loại xe hoặc đi theo tuyến đường khác.", "fa": "مجموع تقریبی کرایهٔ شما بر اساس جزئیات سفر نشان‌داده‌شده در بالاست. اگر مکان سوارشدن یا پیاده‌شدن را تغییر دهید، نوع خودرو را عوض کنید یا از مسیر دیگری استفاده کنید، کرایهٔ نهایی ممکن است تغییر کند", "th": "ค่าโดยสารรวมโดยประมาณของคุณอิงตามรายละเอียดการเดินทางที่แสดงด้านบน ค่าโดยสารสุดท้ายอาจเปลี่ยนแปลงหากคุณเปลี่ยนสถานที่ต้นทางหรือปลายทาง เปลี่ยนประเภทรถยนต์ หรือใช้เส้นทางอื่น"
};

NOEL_I18N["class.note_images"] = {
  "en": "The vehicle images above are examples. You may get a different vehicle of similar quality.", "es": "Las imágenes de los vehículos son ejemplos. Es posible que reciba un vehículo diferente de calidad similar.", "fr": "Les images des véhicules ci-dessus sont des exemples. Vous pouvez recevoir un véhicule différent de qualité similaire.", "ar": "صور السيارات أعلاه أمثلة فقط. قد تحصل على سيارة مختلفة بجودة مماثلة.",
  "pt": "As imagens dos veículos acima são exemplos. Você pode receber um veículo diferente de qualidade semelhante.", "ur": "Upar dikhayi gayi gaariyon ki photos sirf examples hain. Aapko same quality ki koi doosri gaari mil sakti hai.", "hi": "ऊपर दिखाई गई वाहन की तस्वीरें उदाहरण हैं। आपको समान गुणवत्ता का कोई अलग वाहन मिल सकता है।", "bn": "উপরের গাড়ির ছবিগুলো উদাহরণ মাত্র। আপনি একই মানের অন্য গাড়ি পেতে পারেন।",
  "ud": "اوپر کی گاڑی کی تصویر صرف ایک مثال ہے۔ آپ کو اسی طرح کی معیار کی کوئی اور گاڑی مل سکتی ہے", "zh": "上方车辆图片仅为示例。您可能会得到一辆质量相似的不同车辆。", "de": "Die Fahrzeugbilder oben sind Beispiele. Sie erhalten möglicherweise ein anderes Fahrzeug von ähnlicher Qualität.", "it": "Le immagini dei veicoli sopra sono esempi. Potresti ricevere un veicolo diverso di qualità simile.",
  "ru": "Изображения автомобилей выше — примеры. Вам может быть предоставлен другой автомобиль аналогичного качества.", "tr": "Yukarıdaki araç görselleri örnektir. Benzer kalitede farklı bir araç alabilirsiniz.", "ko": "위의 차량 이미지는 예시입니다. 비슷한 품질의 다른 차량이 배정될 수 있습니다.", "ja": "上記の車両画像は例です。類似の品質の別の車両になる場合があります。",
  "vi": "Hình ảnh xe ở trên chỉ là ví dụ. Bạn có thể nhận được một xe khác có chất lượng tương tự.", "fa": "عکس خودرو در بالا فقط یک نمونه است. ممکن است خودروی دیگری با کیفیتی مشابه دریافت کنید", "th": "ภาพรถยนต์ด้านบนเป็นตัวอย่าง คุณอาจได้รับรถยนต์คันอื่นที่มีคุณภาพใกล้เคียงกัน"
};

NOEL_I18N["class.price_breakdown"] = {
  "en": "Price breakdown", "es": "Desglose del precio", "fr": "Détail du prix", "ar": "تفصيل السعر",
  "pt": "Detalhamento do preço", "ur": "Price breakdown", "hi": "कीमत का विवरण", "bn": "মূল্যের বিবরণ",
  "ud": "قیمت کی تفصیل", "zh": "价格明细", "de": "Preisaufschlüsselung", "it": "Dettaglio del prezzo",
  "ru": "Разбивка цены", "tr": "Fiyat dökümü", "ko": "요금 내역", "ja": "料金内訳",
  "vi": "Chi tiết giá", "fa": "جزئیات قیمت", "th": "รายละเอียดราคา"
};

NOEL_I18N["class.select_business_class"] = {
  "en": "Select Business Class", "es": "Seleccionar Business Class", "fr": "Sélectionner Business Class", "ar": "اختر Business Class",
  "pt": "Selecionar Business Class", "ur": "Business Class select karen", "hi": "Business Class चुनें", "bn": "Business Class বেছে নিন",
  "ud": "Business Class منتخب کریں", "zh": "选择 Business Class", "de": "Business Class auswählen", "it": "Seleziona Business Class",
  "ru": "Выбрать Business Class", "tr": "Business Class seçin", "ko": "Business Class 선택", "ja": "Business Classを選択",
  "vi": "Chọn Business Class", "fa": "Business Class را انتخاب کنید", "th": "เลือก Business Class"
};

NOEL_I18N["form.flight"] = {
  "en": "Flight number", "es": "Número de vuelo", "fr": "Numéro de vol", "ar": "رقم الرحلة",
  "pt": "Número do voo", "ur": "Flight number", "hi": "उड़ान संख्या", "bn": "ফ্লাইট নম্বর",
  "ud": "فلائٹ نمبر", "zh": "航班号", "de": "Flugnummer", "it": "Numero di volo",
  "ru": "Номер рейса", "tr": "Uçuş numarası", "ko": "항공편 번호", "ja": "便名",
  "vi": "Số hiệu chuyến bay", "fa": "شمارهٔ پرواز", "th": "หมายเลขเที่ยวบิน"
};

NOEL_I18N["form.phone"] = {
  "en": "Phone number", "es": "Número de teléfono", "fr": "Numéro de téléphone", "ar": "رقم الهاتف",
  "pt": "Número de telefone", "ur": "Phone number", "hi": "फ़ोन नंबर", "bn": "ফোন নম্বর",
  "ud": "فون نمبر", "zh": "电话号码", "de": "Telefonnummer", "it": "Numero di telefono",
  "ru": "Номер телефона", "tr": "Telefon numarası", "ko": "전화번호", "ja": "電話番号",
  "vi": "Số điện thoại", "fa": "شماره تلفن", "th": "หมายเลขโทรศัพท์"
};

NOEL_I18N["form.time"] = {
  "en": "Pickup time", "es": "Hora de recogida", "fr": "Heure de prise en charge", "ar": "وقت الاستلام",
  "pt": "Hora da coleta", "ur": "Pickup time", "hi": "पिकअप का समय", "bn": "পিকআপের সময়",
  "ud": "پک اپ کا وقت", "zh": "上车时间", "de": "Abholzeit", "it": "Ora di ritiro",
  "ru": "Время подачи", "tr": "Biniş saati", "ko": "픽업 시간", "ja": "乗車時刻",
  "vi": "Giờ đón", "fa": "زمان سوارشدن", "th": "เวลารับ"
};

NOEL_I18N["status.card_cvc"] = {
  "en": "CVC", "es": "CVC", "fr": "CVC", "ar": "CVC",
  "pt": "CVC", "ur": "CVC", "hi": "CVC", "bn": "CVC",
  "ud": "CVC", "zh": "CVC", "de": "CVC", "it": "CVC",
  "ru": "CVC", "tr": "CVC", "ko": "CVC", "ja": "CVC",
  "vi": "CVC", "fa": "CVC", "th": "CVC"
};

NOEL_I18N["status.card_expiry"] = {
  "en": "Expiry (MM/YY)", "es": "Caducidad (MM/AA)", "fr": "Expiration (MM/AA)", "ar": "تاريخ الانتهاء (شهر/سنة)",
  "pt": "Validade (MM/AA)", "ur": "Expiry (MM/YY)", "hi": "समाप्ति (MM/YY)", "bn": "মেয়াদ (MM/YY)",
  "ud": "ختم ہونے کی تاریخ (مہینہ/سال)", "zh": "有效期（月/年）", "de": "Gültig bis (MM/JJ)", "it": "Scadenza (MM/AA)",
  "ru": "Срок действия (ММ/ГГ)", "tr": "Son kullanma (AA/YY)", "ko": "만료일(월/년)", "ja": "有効期限（月/年）",
  "vi": "Ngày hết hạn (MM/YY)", "fa": "تاریخ انقضا (ماه/سال)", "th": "วันหมดอายุ (เดือน/ปี)"
};

NOEL_I18N["status.language_label"] = {
  "en": "Language:", "es": "Idioma:", "fr": "Langue :", "ar": "اللغة:",
  "pt": "Idioma:", "ur": "Language:", "hi": "भाषा:", "bn": "ভাষা:",
  "ud": "زبان:", "zh": "语言：", "de": "Sprache:", "it": "Lingua:",
  "ru": "Язык:", "tr": "Dil:", "ko": "언어:", "ja": "言語：",
  "vi": "Ngôn ngữ:", "fa": "زبان:", "th": "ภาษา:"
};

NOEL_I18N["status.on_way"] = {
  "en": "Your chauffeur is on the way.", "es": "Tu chófer está en camino.", "fr": "Votre chauffeur est en route.", "ar": "سائقك في الطريق إليك.",
  "pt": "Seu motorista está a caminho.", "ur": "Aapka chauffeur raste mein hai.", "hi": "आपका चालक रास्ते में है।", "bn": "আপনার চালক পথে আছেন।",
  "ud": "آپ کا ڈرائیور آ رہا ہے", "zh": "您的司机正在路上。", "de": "Ihr Chauffeur ist auf dem Weg.", "it": "Il tuo chauffeur è in arrivo.",
  "ru": "Ваш шофёр в пути.", "tr": "Şoförünüz yolda.", "ko": "쇼퍼가 오는 중입니다.", "ja": "ショファーが向かっています。",
  "vi": "Tài xế của bạn đang trên đường.", "fa": "رانندهٔ شما در راه است", "th": "คนขับของคุณกำลังมา"
};

NOEL_I18N["status.on_way_title"] = {
  "en": "Your chauffeur on the way", "es": "Tu chófer en camino", "fr": "Votre chauffeur en route", "ar": "سائقك في الطريق",
  "pt": "Seu motorista a caminho", "ur": "Aapka chauffeur raste mein", "hi": "आपका चालक रास्ते में", "bn": "আপনার চালক পথে",
  "ud": "آپ کا ڈرائیور آ رہا ہے", "zh": "您的司机正在路上", "de": "Ihr Chauffeur ist auf dem Weg", "it": "Il tuo chauffeur è in arrivo",
  "ru": "Ваш шофёр в пути", "tr": "Şoförünüz yolda", "ko": "쇼퍼가 오는 중입니다", "ja": "ショファーが向かっています",
  "vi": "Tài xế của bạn đang trên đường", "fa": "رانندهٔ شما در راه است", "th": "คนขับของคุณกำลังมา"
};

NOEL_I18N["status.pay"] = {
  "en": "Pay", "es": "Pagar", "fr": "Payer", "ar": "ادفع",
  "pt": "Pagar", "ur": "Pay karen", "hi": "भुगतान करें", "bn": "পে করুন",
  "ud": "ادائیگی کریں", "zh": "支付", "de": "Bezahlen", "it": "Paga",
  "ru": "Оплатить", "tr": "Öde", "ko": "결제", "ja": "支払う",
  "vi": "Thanh toán", "fa": "پرداخت", "th": "ชำระเงิน"
};

NOEL_I18N["status.pay_unavailable"] = {
  "en": "Card payments are not set up yet. Please try again later.", "es": "Los pagos con tarjeta aún no están configurados. Inténtalo de nuevo más tarde.", "fr": "Les paiements par carte ne sont pas encore configurés. Veuillez réessayer plus tard.", "ar": "الدفع بالبطاقة غير مُعد بعد. يرجى المحاولة مرة أخرى لاحقًا.",
  "pt": "Os pagamentos com cartão ainda não estão configurados. Tente novamente mais tarde.", "ur": "Card payments abhi set up nahi hain. Please baad mein phir try karen.", "hi": "कार्ड भुगतान अभी सेट नहीं है। कृपया बाद में पुनः प्रयास करें।", "bn": "কার্ড পেমেন্ট এখনো সেট আপ হয়নি। পরে আবার চেষ্টা করুন।",
  "ud": "کارڈ سے ادائیگی ابھی سیٹ اپ نہیں ہوئی ہے، براہ کرم بعد میں دوبارہ کوشش کریں", "zh": "卡支付尚未设置。请稍后再试。", "de": "Kartenzahlungen sind noch nicht eingerichtet. Bitte versuchen Sie es später erneut.", "it": "I pagamenti con carta non sono ancora attivi. Riprova più tardi.",
  "ru": "Оплата картой пока не настроена. Пожалуйста, попробуйте позже.", "tr": "Kart ödemeleri henüz kurulmadı. Lütfen daha sonra tekrar deneyin.", "ko": "카드 결제가 아직 설정되지 않았습니다. 나중에 다시 시도해 주세요.", "ja": "カード決済はまだ設定されていません。後でもう一度お試しください。",
  "vi": "Thanh toán bằng thẻ chưa được thiết lập. Vui lòng thử lại sau.", "fa": "پرداخت با کارت هنوز راه‌اندازی نشده است، لطفاً بعداً دوباره تلاش کنید", "th": "ยังไม่ได้ตั้งค่าการชำระเงินด้วยบัตร โปรดลองอีกครั้งในภายหลัง"
};

NOEL_I18N["status.single_total"] = {
  "en": "One single total for your ride. No breakdown, no hidden charges.", "es": "Un solo total para tu viaje. Sin desglose, sin cargos ocultos.", "fr": "Un seul total pour votre trajet. Aucun détail, aucun frais caché.", "ar": "إجمالي واحد لرحلتك. لا تفصيل ولا رسوم خفية.",
  "pt": "Um único total para sua viagem. Sem detalhamento, sem taxas ocultas.", "ur": "Aapki ride ke liye ek hi total. Koi breakdown nahi, koi hidden charges nahi.", "hi": "आपकी सवारी के लिए एक ही कुल राशि। कोई विवरण नहीं, कोई छिपा शुल्क नहीं।", "bn": "আপনার রাইডের জন্য একটাই মোট। কোনো বিবরণ নেই, কোনো লুকানো চার্জ নেই।",
  "ud": "آپ کی سواری کے لیے ایک کل رقم، کوئی تفصیل نہیں، کوئی پوشیدہ چارج نہیں", "zh": "您的行程只有一个总价。无明细，无隐藏费用。", "de": "Ein einziger Gesamtpreis für Ihre Fahrt. Keine Aufschlüsselung, keine versteckten Kosten.", "it": "Un unico totale per la tua corsa. Nessun dettaglio, nessun costo nascosto.",
  "ru": "Одна общая стоимость вашей поездки. Без разбивки, без скрытых платежей.", "tr": "Yolculuğunuz için tek bir toplam. Döküm yok, gizli ücret yok.", "ko": "이동에 대한 단일 총액입니다. 내역도, 숨은 요금도 없습니다.", "ja": "乗車の合計は1つだけです。内訳も隠れた料金もありません。",
  "vi": "Một tổng giá duy nhất cho chuyến đi của bạn. Không chi tiết, không phí ẩn.", "fa": "یک مجموع برای سفر شما، بدون جزئیات، بدون هزینهٔ پنهان", "th": "ยอดรวมเดียวสำหรับการเดินทางของคุณ ไม่มีการแยกย่อย ไม่มีค่าใช้จ่ายแอบแฝง"
};

NOEL_I18N["status.stripe_note"] = {
  "en": "Your card is charged as a hold when you book. Your card details go directly to Stripe — they are never typed into, or stored on, this site.", "es": "Tu tarjeta se carga como retención al reservar. Los datos de tu tarjeta van directamente a Stripe: nunca se escriben ni se guardan en este sitio.", "fr": "Votre carte est débitée à titre de garantie lors de la réservation. Les coordonnées de votre carte vont directement à Stripe — elles ne sont jamais saisies ni stockées sur ce site.", "ar": "يتم خصم بطاقتك كحجز مؤقت عند الحجز. تذهب بيانات بطاقتك مباشرة إلى Stripe — ولا تُكتب أو تُخزَّن أبدًا على هذا الموقع.",
  "pt": "Seu cartão é cobrado como retenção ao reservar. Os dados do cartão vão diretamente para a Stripe — nunca são digitados nem armazenados neste site.", "ur": "Book karte waqt aapke card par hold lagaya jata hai. Aapke card ki details seedha Stripe ko jati hain — ye is site par kabhi type ya save nahi hoti.", "hi": "बुक करते समय आपके कार्ड पर होल्ड लगाया जाता है। आपके कार्ड का विवरण सीधे Stripe को जाता है — यह इस साइट पर कभी टाइप या संग्रहीत नहीं होता।", "bn": "বুক করার সময় আপনার কার্ডে হোল্ড চার্জ করা হয়। আপনার কার্ডের বিবরণ সরাসরি Stripe-এ যায় — এটি এই সাইটে কখনো টাইপ বা সংরক্ষণ করা হয় না।",
  "ud": "جب آپ بک کریں گے تو آپ کے کارڈ پر ہولڈ لگایا جائے گا۔ آپ کے کارڈ کی تفصیلات براہ راست Stripe کو بھیجی جاتی ہیں — وہ نہ تو اس ویب سائٹ پر ٹائپ کی جاتی ہیں اور نہ ہی محفوظ کی جاتی ہیں", "zh": "预订时您的卡将被预授权扣款。您的卡信息直接发送给 Stripe——绝不会在本网站输入或存储。", "de": "Ihre Karte wird bei der Buchung als Kaution belastet. Ihre Kartendaten gehen direkt an Stripe — sie werden auf dieser Seite weder eingegeben noch gespeichert.", "it": "La tua carta viene addebitata come deposito quando prenoti. I dati della tua carta vanno direttamente a Stripe — non vengono mai digitati né memorizzati su questo sito.",
  "ru": "Ваша карта списывается как залог при бронировании. Данные вашей карты направляются напрямую в Stripe — они никогда не вводятся и не хранятся на этом сайте.", "tr": "Kartınızdan rezervasyon yaparken provizyon alınır. Kart bilgileriniz doğrudan Stripe'a gider — bu siteye hiçbir zaman yazılmaz veya burada saklanmaz.", "ko": "예약 시 카드에 보류 결제가 청구됩니다. 카드 정보는 Stripe으로 직접 전송되며 이 사이트에 입력되거나 저장되지 않습니다.", "ja": "予約時にカードに仮請求がかかります。カード詳細はStripeに直接送信されます。このサイトに入力されたり保存されたりすることは決してありません。",
  "vi": "Thẻ của bạn sẽ bị giữ tiền khi bạn đặt xe. Chi tiết thẻ của bạn được gửi trực tiếp đến Stripe — chúng không bao giờ được nhập vào, hay lưu trữ trên, trang web này.", "fa": "هنگام رزرو، مبلغی روی کارت شما مسدود می‌شود. جزئیات کارت شما مستقیماً به Stripe ارسال می‌شود — در این وب‌سایت نه تایپ و نه ذخیره می‌شود", "th": "บัตรของคุณจะถูกกันวงเงินเมื่อคุณจอง รายละเอียดบัตรของคุณส่งตรงไปยัง Stripe — จะไม่มีการพิมพ์ลงใน หรือจัดเก็บไว้บน เว็บไซต์นี้"
};

NOEL_I18N["status.thankyou_test"] = {
  "en": "Test mode — no real charge. This booking was paid in test mode; no real payment was taken.", "es": "Modo de prueba: sin cargo real. Esta reserva se pagó en modo de prueba; no se realizó ningún pago real.", "fr": "Mode test — aucun débit réel. Cette réservation a été payée en mode test ; aucun paiement réel n'a été effectué.", "ar": "وضع الاختبار — لا يوجد خصم حقيقي. تم دفع هذا الحجز في وضع الاختبار؛ ولم يتم أخذ أي دفعة حقيقية.",
  "pt": "Modo de teste — sem cobrança real. Esta reserva foi paga em modo de teste; nenhum pagamento real foi feito.", "ur": "Test mode — koi real charge nahi. Ye booking test mode mein pay ki gayi thi; koi real payment nahi li gayi.", "hi": "परीक्षण मोड — कोई वास्तविक शुल्क नहीं। यह बुकिंग परीक्षण मोड में भुगतान की गई थी; कोई वास्तविक भुगतान नहीं लिया गया।", "bn": "টেস্ট মোড — কোনো আসল চার্জ নেই। এই বুকিং টেস্ট মোডে পে করা হয়েছিল; কোনো আসল পেমেন্ট নেওয়া হয়নি।",
  "ud": "ٹیسٹ موڈ — کوئی حقیقی چارج نہیں۔ یہ بکنگ ٹیسٹ موڈ میں ادا کی گئی تھی، کوئی حقیقی ادائیگی نہیں ہوئی", "zh": "测试模式——不收取实际费用。此预订已在测试模式下支付；未收取实际付款。", "de": "Testmodus — keine echte Abbuchung. Diese Buchung wurde im Testmodus bezahlt; es wurde keine echte Zahlung vorgenommen.", "it": "Modalità test — nessun addebito reale. Questa prenotazione è stata pagata in modalità test; non è stato effettuato alcun pagamento reale.",
  "ru": "Тестовый режим — реальная оплата не списывается. Это бронирование было оплачено в тестовом режиме; реальный платёж не был списан.", "tr": "Test modu — gerçek ücret alınmaz. Bu rezervasyon test modunda ödendi; gerçek bir ödeme alınmadı.", "ko": "테스트 모드 — 실제 요금이 청구되지 않습니다. 이 예약은 테스트 모드로 결제되었으며 실제 결제는 이루어지지 않았습니다.", "ja": "テストモード — 実際の請求はありません。この予約はテストモードで支払われました。実際の支払いは行われていません。",
  "vi": "Chế độ thử nghiệm — không tính phí thật. Đặt xe này đã được thanh toán trong chế độ thử nghiệm; không có khoản thanh toán thật nào được thực hiện.", "fa": "حالت آزمایشی — هیچ هزینهٔ واقعی نیست. این رزرو در حالت آزمایشی پرداخت شد، هیچ پرداخت واقعی صورت نگرفت", "th": "โหมดทดสอบ — ไม่มีการเรียกเก็บเงินจริง การจองนี้ชำระในโหมดทดสอบ ไม่มีการชำระเงินจริง"
};

NOEL_I18N["status.waiting_charge"] = {
  "en": "Waiting charge", "es": "Cargo por espera", "fr": "Frais d'attente", "ar": "رسوم الانتظار",
  "pt": "Taxa de espera", "ur": "Waiting charge", "hi": "प्रतीक्षा शुल्क", "bn": "অপেক্ষার চার্জ",
  "ud": "انتظار کا چارج", "zh": "等候费", "de": "Wartegebühr", "it": "Supplemento di attesa",
  "ru": "Плата за ожидание", "tr": "Bekleme ücreti", "ko": "대기 요금", "ja": "待ち料金",
  "vi": "Phí chờ", "fa": "هزینهٔ انتظار", "th": "ค่ารอ"
};

NOEL_I18N["class.hourly_miles_note"] = {
  "en": "Includes {miles} miles of travel ({mph} miles per hour) — taxes and tolls included.", "es": "Incluye {miles} millas de viaje ({mph} millas por hora); impuestos y peajes incluidos.", "fr": "Comprend {miles} miles de trajet ({mph} miles par heure) — taxes et péages inclus.", "ar": "يشمل {miles} ميلًا من السفر ({mph} ميلًا في الساعة) — الضرائب والرسوم مشمولة.",
  "pt": "Inclui {miles} milhas de viagem ({mph} milhas por hora) — impostos e pedágios incluídos.", "ur": "{miles} miles ka safar shamil hai ({mph} miles per hour) — taxes aur tolls shamil hain.", "hi": "{miles} मील की यात्रा शामिल है ({mph} मील प्रति घंटा) — कर और टोल शामिल हैं।", "bn": "{miles} মাইল ভ্রমণ অন্তর্ভুক্ত ({mph} মাইল প্রতি ঘণ্টা) — ট্যাক্স ও টোল অন্তর্ভুক্ত।",
  "ud": "{miles} میل شامل ہیں ({mph} میل فی گھنٹہ) — ٹیکس اور ٹول شامل ہیں", "zh": "包含 {miles} 英里行程（每小时 {mph} 英里）——税费和过路费已包含。", "de": "Inklusive {miles} Meilen Fahrt ({mph} Meilen pro Stunde) — Steuern und Maut inklusive.", "it": "Include {miles} miglia di viaggio ({mph} miglia all'ora) — tasse e pedaggi inclusi.",
  "ru": "Включает {miles} миль поездки ({mph} миль в час) — налоги и сборы включены.", "tr": "{miles} mil yolculuk dahildir ({mph} mil/saat) — vergiler ve geçiş ücretleri dahildir.", "ko": "{miles}마일 이동 포함(시간당 {mph}마일) — 세금 및 통행료 포함.", "ja": "{miles}マイルの走行を含む（1時間あたり{mph}マイル）— 税金と通行料込み。",
  "vi": "Bao gồm {miles} dặm di chuyển ({mph} dặm mỗi giờ) — đã bao gồm thuế và phí cầu đường.", "fa": "{miles} مایل شامل است ({mph} مایل در ساعت) — مالیات و عوارض شامل است", "th": "รวมระยะทาง {miles} ไมล์ ({mph} ไมล์ต่อชั่วโมง) — รวมภาษีและค่าผ่านทางแล้ว"
};

NOEL_I18N["class.select_class"] = {
  "en": "Select {label}", "es": "Seleccionar {label}", "fr": "Sélectionner {label}", "ar": "اختر {label}",
  "pt": "Selecionar {label}", "ur": "{label} select karen", "hi": "{label} चुनें", "bn": "{label} বেছে নিন",
  "ud": "{label} منتخب کریں", "zh": "选择{label}", "de": "{label} auswählen", "it": "Seleziona {label}",
  "ru": "Выбрать {label}", "tr": "{label} seçin", "ko": "{label} 선택", "ja": "{label}を選択",
  "vi": "Chọn {label}", "fa": "{label} را انتخاب کنید", "th": "เลือก {label}"
};

NOEL_I18N["class.hour_suffix"] = {
  "en": " hour(s)", "es": " hora(s)", "fr": " heure(s)", "ar": " ساعة",
  "pt": " hora(s)", "ur": " hour(s)", "hi": " घंटा", "bn": " ঘণ্টা",
  "ud": " گھنٹے", "zh": " 小时", "de": " Stunde(n)", "it": " ora(e)",
  "ru": " час(а)", "tr": " saat", "ko": " 시간", "ja": " 時間",
  "vi": " giờ", "fa": " ساعت", "th": " ชั่วโมง"
};

NOEL_I18N["status.return_trip_label"] = {
  "en": "Return trip", "es": "Viaje de regreso", "fr": "Trajet retour", "ar": "رحلة العودة",
  "pt": "Viagem de volta", "ur": "Return trip", "hi": "वापसी यात्रा", "bn": "ফেরার ট্রিপ",
  "ud": "واپسی کی سواری", "zh": "返程", "de": "Rückfahrt", "it": "Viaggio di ritorno",
  "ru": "Обратная поездка", "tr": "Dönüş yolculuğu", "ko": "귀환 여정", "ja": "帰りの乗車",
  "vi": "Chuyến về", "fa": "سفر برگشت", "th": "เที่ยวกลับ"
};

NOEL_I18N["status.one_way_label"] = {
  "en": "One way", "es": "Solo ida", "fr": "Aller simple", "ar": "ذهاب فقط",
  "pt": "Somente ida", "ur": "One way", "hi": "एक तरफ़ा", "bn": "ওয়ান ওয়ে",
  "ud": "ایک طرفہ", "zh": "单程", "de": "Einfache Fahrt", "it": "Solo andata",
  "ru": "В одну сторону", "tr": "Tek yön", "ko": "편도", "ja": "片道",
  "vi": "Một chiều", "fa": "یک‌طرفه", "th": "เที่ยวเดียว"
};

NOEL_I18N["status.awaiting_payment"] = {
  "en": "Payment needed to confirm your ride", "es": "Pago necesario para confirmar tu viaje", "fr": "Paiement requis pour confirmer votre trajet", "ar": "يلزم الدفع لتأكيد رحلتك",
  "pt": "Pagamento necessário para confirmar sua viagem", "ur": "Aapki ride confirm karne ke liye payment zaroori hai", "hi": "आपकी सवारी की पुष्टि के लिए भुगतान आवश्यक है", "bn": "আপনার রাইড নিশ্চিত করতে পেমেন্ট প্রয়োজন",
  "ud": "اپنی سواری کی تصدیق کے لیے ادائیگی درکار ہے", "zh": "需要付款以确认您的行程", "de": "Zahlung erforderlich, um Ihre Fahrt zu bestätigen", "it": "Pagamento necessario per confermare la tua corsa",
  "ru": "Требуется оплата для подтверждения вашей поездки", "tr": "Yolculuğunuzu onaylamak için ödeme gerekli", "ko": "이동 확인을 위해 결제가 필요합니다", "ja": "乗車を確定するにはお支払いが必要です",
  "vi": "Cần thanh toán để xác nhận chuyến đi của bạn", "fa": "برای تأیید سفر خود، پرداخت لازم است", "th": "ต้องชำระเงินเพื่อยืนยันการเดินทางของคุณ"
};

NOEL_I18N["status.offered"] = {
  "en": "Finding your chauffeur…", "es": "Buscando tu chófer…", "fr": "Recherche de votre chauffeur…", "ar": "جارٍ البحث عن سائقك…",
  "pt": "Procurando seu motorista…", "ur": "Aapka chauffeur dhoondha ja raha hai…", "hi": "आपका चालक खोजा जा रहा है…", "bn": "আপনার চালক খোঁজা হচ্ছে…",
  "ud": "آپ کے لیے ڈرائیور تلاش کیا جا رہا ہے…", "zh": "正在为您寻找司机…", "de": "Ihr Chauffeur wird gesucht…", "it": "Ricerca del tuo chauffeur…",
  "ru": "Поиск вашего шофёра…", "tr": "Şoförünüz aranıyor…", "ko": "쇼퍼를 찾고 있습니다…", "ja": "ショファーを探しています…",
  "vi": "Đang tìm tài xế cho bạn…", "fa": "در حال یافتن راننده برای شما…", "th": "กำลังหาคนขับให้คุณ…"
};

NOEL_I18N["status.accepted"] = {
  "en": "Chauffeur confirmed", "es": "Chófer confirmado", "fr": "Chauffeur confirmé", "ar": "تم تأكيد السائق",
  "pt": "Motorista confirmado", "ur": "Chauffeur confirmed", "hi": "चालक की पुष्टि हो गई", "bn": "চালক নিশ্চিত হয়েছে",
  "ud": "ڈرائیور کی تصدیق ہو گئی", "zh": "司机已确认", "de": "Chauffeur bestätigt", "it": "Chauffeur confermato",
  "ru": "Шофёр подтверждён", "tr": "Şoför onaylandı", "ko": "쇼퍼 확인됨", "ja": "ショファーが確認されました",
  "vi": "Tài xế đã xác nhận", "fa": "راننده تأیید شد", "th": "ยืนยันคนขับแล้ว"
};

NOEL_I18N["status.en_route"] = {
  "en": "Your chauffeur is on the way", "es": "Tu chófer está en camino", "fr": "Votre chauffeur est en route", "ar": "سائقك في الطريق",
  "pt": "Seu motorista está a caminho", "ur": "Aapka chauffeur raste mein hai", "hi": "आपका चालक रास्ते में है", "bn": "আপনার চালক পথে আছেন",
  "ud": "آپ کا ڈرائیور آ رہا ہے", "zh": "您的司机正在路上", "de": "Ihr Chauffeur ist auf dem Weg", "it": "Il tuo chauffeur è in arrivo",
  "ru": "Ваш шофёр в пути", "tr": "Şoförünüz yolda", "ko": "쇼퍼가 오는 중입니다", "ja": "ショファーが向かっています",
  "vi": "Tài xế của bạn đang trên đường", "fa": "رانندهٔ شما در راه است", "th": "คนขับของคุณกำลังมา"
};

NOEL_I18N["status.started"] = {
  "en": "Your ride is under way", "es": "Tu viaje está en curso", "fr": "Votre trajet est en cours", "ar": "رحلتك جارية",
  "pt": "Sua viagem está em andamento", "ur": "Aapki ride chal rahi hai", "hi": "आपकी सवारी चल रही है", "bn": "আপনার রাইড চলছে",
  "ud": "آپ کی سواری جاری ہے", "zh": "您的行程正在进行中", "de": "Ihre Fahrt ist unterwegs", "it": "La tua corsa è in corso",
  "ru": "Ваша поездка в пути", "tr": "Yolculuğunuz devam ediyor", "ko": "이동이 진행 중입니다", "ja": "乗車中です",
  "vi": "Chuyến đi của bạn đang diễn ra", "fa": "سفر شما در جریان است", "th": "การเดินทางของคุณกำลังดำเนินอยู่"
};

NOEL_I18N["status.on_trip"] = {
  "en": "Your ride is under way", "es": "Tu viaje está en curso", "fr": "Votre trajet est en cours", "ar": "رحلتك جارية",
  "pt": "Sua viagem está em andamento", "ur": "Aapki ride chal rahi hai", "hi": "आपकी सवारी चल रही है", "bn": "আপনার রাইড চলছে",
  "ud": "آپ کی سواری جاری ہے", "zh": "您的行程正在进行中", "de": "Ihre Fahrt ist unterwegs", "it": "La tua corsa è in corso",
  "ru": "Ваша поездка в пути", "tr": "Yolculuğunuz devam ediyor", "ko": "이동이 진행 중입니다", "ja": "乗車中です",
  "vi": "Chuyến đi của bạn đang diễn ra", "fa": "سفر شما در جریان است", "th": "การเดินทางของคุณกำลังดำเนินอยู่"
};

NOEL_I18N["status.in_progress"] = {
  "en": "Your ride is under way", "es": "Tu viaje está en curso", "fr": "Votre trajet est en cours", "ar": "رحلتك جارية",
  "pt": "Sua viagem está em andamento", "ur": "Aapki ride chal rahi hai", "hi": "आपकी सवारी चल रही है", "bn": "আপনার রাইড চলছে",
  "ud": "آپ کی سواری جاری ہے", "zh": "您的行程正在进行中", "de": "Ihre Fahrt ist unterwegs", "it": "La tua corsa è in corso",
  "ru": "Ваша поездка в пути", "tr": "Yolculuğunuz devam ediyor", "ko": "이동이 진행 중입니다", "ja": "乗車中です",
  "vi": "Chuyến đi của bạn đang diễn ra", "fa": "سفر شما در جریان است", "th": "การเดินทางของคุณกำลังดำเนินอยู่"
};

NOEL_I18N["status.completed"] = {
  "en": "Ride completed — thank you", "es": "Viaje completado — gracias", "fr": "Trajet terminé — merci", "ar": "اكتملت الرحلة — شكرًا",
  "pt": "Viagem concluída — obrigado", "ur": "Ride complete — shukriya", "hi": "सवारी पूरी हो गई — धन्यवाद", "bn": "রাইড সম্পন্ন হয়েছে — ধন্যবাদ",
  "ud": "سواری مکمل ہو گئی — شکریہ", "zh": "行程已完成——谢谢", "de": "Fahrt abgeschlossen — vielen Dank", "it": "Corsa completata — grazie",
  "ru": "Поездка завершена — спасибо", "tr": "Yolculuk tamamlandı — teşekkürler", "ko": "이동 완료 — 감사합니다", "ja": "乗車が完了しました — ありがとうございます",
  "vi": "Chuyến đi đã hoàn thành — cảm ơn bạn", "fa": "سفر تکمیل شد — متشکریم", "th": "การเดินทางเสร็จสิ้น — ขอบคุณ"
};

NOEL_I18N["status.cancelled"] = {
  "en": "This booking was cancelled", "es": "Esta reserva fue cancelada", "fr": "Cette réservation a été annulée", "ar": "تم إلغاء هذا الحجز",
  "pt": "Esta reserva foi cancelada", "ur": "Ye booking cancel ho gayi thi", "hi": "यह बुकिंग रद्द कर दी गई थी", "bn": "এই বুকিং বাতিল করা হয়েছিল",
  "ud": "یہ بکنگ منسوخ کر دی گئی ہے", "zh": "此预订已取消", "de": "Diese Buchung wurde storniert", "it": "Questa prenotazione è stata annullata",
  "ru": "Это бронирование было отменено", "tr": "Bu rezervasyon iptal edildi", "ko": "이 예약이 취소되었습니다", "ja": "この予約はキャンセルされました",
  "vi": "Đặt xe này đã bị hủy", "fa": "این رزرو لغو شده است", "th": "การจองนี้ถูกยกเลิกแล้ว"
};

NOEL_I18N["class.explore_class"] = {
  "en": "Explore {label} details", "es": "Explorar los detalles de {label}", "fr": "Explorer les détails de {label}", "ar": "استكشف تفاصيل {label}",
  "pt": "Explorar detalhes de {label}", "ur": "{label} ki details dekhen", "hi": "{label} का विवरण देखें", "bn": "{label}-এর বিবরণ দেখুন",
  "ud": "{label} کی تفصیل دیکھیں", "zh": "查看{label}详情", "de": "{label}-Details ansehen", "it": "Vedi i dettagli di {label}",
  "ru": "Подробнее о {label}", "tr": "{label} ayrıntılarını keşfedin", "ko": "{label} 자세히 보기", "ja": "{label}の詳細を見る",
  "vi": "Khám phá chi tiết {label}", "fa": "مشاهدهٔ جزئیات {label}", "th": "สำรวจรายละเอียด {label}"
};

NOEL_I18N["class.carry_on"] = {
  "en": "{n} x Carry-on", "es": "{n} x equipaje de mano", "fr": "{n} x bagage cabine", "ar": "{n} × حقيبة يد",
  "pt": "{n} x bagagem de mão", "ur": "{n} x Carry-on", "hi": "{n} x केबिन बैग", "bn": "{n} x ক্যারি-অন",
  "ud": "{n} x کیری آن", "zh": "{n} x 随身行李", "de": "{n} x Handgepäck", "it": "{n} x bagaglio a mano",
  "ru": "{n} x ручная кладь", "tr": "{n} x kabin bagajı", "ko": "{n} x 기내 수하물", "ja": "{n} x 機内持ち込み手荷物",
  "vi": "{n} x hành lý xách tay", "fa": "{n} x چمدان دستی", "th": "{n} x กระเป๋าถือขึ้นเครื่อง"
};

NOEL_I18N["class.passengers_count"] = {
  "en": "{n} passengers", "es": "{n} pasajeros", "fr": "{n} passagers", "ar": "{n} ركاب",
  "pt": "{n} passageiros", "ur": "{n} passengers", "hi": "{n} यात्री", "bn": "{n} জন যাত্রী",
  "ud": "{n} مسافر", "zh": "{n} 位乘客", "de": "{n} Passagiere", "it": "{n} passeggeri",
  "ru": "{n} пассажиров", "tr": "{n} yolcu", "ko": "{n}명 승객", "ja": "{n}名の乗客",
  "vi": "{n} hành khách", "fa": "{n} مسافر", "th": "{n} ผู้โดยสาร"
};

NOEL_I18N["class.highlight_n"] = {
  "en": "Highlight {n}", "es": "Aspecto {n}", "fr": "Point fort {n}", "ar": "الميزة {n}",
  "pt": "Destaque {n}", "ur": "Highlight {n}", "hi": "विशेषता {n}", "bn": "হাইলাইট {n}",
  "ud": "نمایاں بات {n}", "zh": "亮点 {n}", "de": "Highlight {n}", "it": "Evidenza {n}",
  "ru": "Преимущество {n}", "tr": "Öne çıkan {n}", "ko": "특징 {n}", "ja": "ハイライト {n}",
  "vi": "Điểm nổi bật {n}", "fa": "ویژگی {n}", "th": "จุดเด่น {n}"
};

NOEL_I18N["class.referral_discount_row"] = {
  "en": "Referral discount", "es": "Descuento por recomendación", "fr": "Remise de parrainage", "ar": "خصم الإحالة",
  "pt": "Desconto por indicação", "ur": "Referral discount", "hi": "रेफ़रल छूट", "bn": "রেফারেল ছাড়",
  "ud": "تجویزی رعایت", "zh": "推荐折扣", "de": "Empfehlungsrabatt", "it": "Sconto referral",
  "ru": "Реферальная скидка", "tr": "Referans indirimi", "ko": "추천 할인", "ja": "紹介割引",
  "vi": "Giảm giá giới thiệu", "fa": "تخفیف معرفی", "th": "ส่วนลดแนะนำ"
};

NOEL_I18N["form.paused_msg"] = {
  "en": "Bookings are paused while we update our prices. Please check back soon.", "es": "Las reservas están en pausa mientras actualizamos los precios. Vuelve a intentarlo pronto.", "fr": "Les réservations sont en pause pendant la mise à jour de nos prix. Veuillez revenir bientôt.", "ar": "الحجوزات متوقفة مؤقتًا أثناء تحديث أسعارنا. يرجى العودة قريبًا.",
  "pt": "As reservas estão pausadas enquanto atualizamos os preços. Volte em breve.", "ur": "Prices update karte waqt bookings paused hain. Please thodi der mein phir check karen.", "hi": "हमारी कीमतें अपडेट करते समय बुकिंग रुकी हुई है। कृपया जल्द ही फिर से देखें।", "bn": "আমরা দাম আপডেট করার সময় বুকিং বন্ধ আছে। শীঘ্রই আবার দেখুন।",
  "ud": "قیمتوں کو اپ ڈیٹ کرتے وقت بکنگ عارضی طور پر رکی ہوئی ہے، براہ کرم جلد دوبارہ چیک کریں", "zh": "我们正在更新价格，预订已暂停。请稍后再查看。", "de": "Buchungen sind pausiert, während wir unsere Preise aktualisieren. Bitte schauen Sie bald wieder vorbei.", "it": "Le prenotazioni sono in pausa mentre aggiorniamo i nostri prezzi. Torna a trovarci presto.",
  "ru": "Бронирование приостановлено, пока мы обновляем наши цены. Пожалуйста, зайдите позже.", "tr": "Fiyatlarımızı güncellerken rezervasyonlar duraklatıldı. Lütfen yakında tekrar kontrol edin.", "ko": "가격 업데이트 중 예약이 중단되었습니다. 곧 다시 확인해 주세요.", "ja": "料金更新のため、予約を一時停止しています。しばらくしてから再度ご確認ください。",
  "vi": "Đặt xe đang tạm dừng trong khi chúng tôi cập nhật giá. Vui lòng kiểm tra lại sớm.", "fa": "رزرو در حین به‌روزرسانی قیمت‌ها موقتاً متوقف است، لطفاً به‌زودی دوباره بررسی کنید", "th": "การจองหยุดชั่วคราวในขณะที่เราปรับปรุงราคา โปรดกลับมาตรวจสอบอีกครั้งเร็วๆ นี้"
};

NOEL_I18N["form.hourly_hours_error"] = {
  "en": "Hourly bookings need 2 to 24 hours.", "es": "Las reservas por horas necesitan de 2 a 24 horas.", "fr": "Les réservations à l'heure nécessitent de 2 à 24 heures.", "ar": "الحجوزات بالساعة تحتاج من ساعتين إلى 24 ساعة.",
  "pt": "Reservas por hora precisam de 2 a 24 horas.", "ur": "Hourly bookings ke liye 2 se 24 hours chahiye.", "hi": "प्रति घंटा बुकिंग के लिए 2 से 24 घंटे चाहिए।", "bn": "ঘণ্টাভিত্তিক বুকিংয়ের জন্য ২ থেকে ২৪ ঘণ্টা প্রয়োজন।",
  "ud": "فی گھنٹہ بکنگ کے لیے 2 سے 24 گھنٹے درکار ہیں", "zh": "按小时预订需要2至24小时。", "de": "Stundenweise Buchungen erfordern 2 bis 24 Stunden.", "it": "Le prenotazioni a ore richiedono da 2 a 24 ore.",
  "ru": "Почасовое бронирование требует от 2 до 24 часов.", "tr": "Saatlik rezervasyonlar 2 ila 24 saat gerektirir.", "ko": "시간제 예약은 2~24시간이 필요합니다.", "ja": "時間貸しの予約には2〜24時間が必要です。",
  "vi": "Đặt xe theo giờ cần 2 đến 24 giờ.", "fa": "رزرو ساعتی به ۲ تا ۲۴ ساعت نیاز دارد", "th": "การจองรายชั่วโมงต้องใช้ 2 ถึง 24 ชั่วโมง"
};

NOEL_I18N["form.choose_date_time"] = {
  "en": "Please choose a date and time.", "es": "Elige una fecha y una hora.", "fr": "Veuillez choisir une date et une heure.", "ar": "يرجى اختيار تاريخ ووقت.",
  "pt": "Escolha uma data e hora.", "ur": "Please date aur time chunen.", "hi": "कृपया तारीख़ और समय चुनें।", "bn": "একটি তারিখ ও সময় বেছে নিন।",
  "ud": "براہ کرم تاریخ اور وقت منتخب کریں", "zh": "请选择日期和时间。", "de": "Bitte wählen Sie Datum und Uhrzeit.", "it": "Scegli data e ora.",
  "ru": "Пожалуйста, выберите дату и время.", "tr": "Lütfen bir tarih ve saat seçin.", "ko": "날짜와 시간을 선택해 주세요.", "ja": "日付と時刻を選択してください。",
  "vi": "Vui lòng chọn ngày và giờ.", "fa": "لطفاً تاریخ و زمان را انتخاب کنید", "th": "โปรดเลือกวันที่และเวลา"
};

NOEL_I18N["class.fill_details"] = {
  "en": "Please fill in your name, phone and email.", "es": "Completa tu nombre, teléfono y correo electrónico.", "fr": "Veuillez renseigner votre nom, votre téléphone et votre e-mail.", "ar": "يرجى إدخال اسمك ورقم هاتفك وبريدك الإلكتروني.",
  "pt": "Preencha seu nome, telefone e e-mail.", "ur": "Please apna naam, phone aur email likhen.", "hi": "कृपया अपना नाम, फ़ोन और ईमेल लिखें।", "bn": "আপনার নাম, ফোন ও ইমেইল লিখুন।",
  "ud": "براہ کرم اپنا نام، فون اور ای میل درج کریں", "zh": "请填写您的姓名、电话和邮箱。", "de": "Bitte geben Sie Ihren Namen, Ihre Telefonnummer und Ihre E-Mail-Adresse ein.", "it": "Inserisci nome, telefono ed email.",
  "ru": "Пожалуйста, введите ваше имя, телефон и электронную почту.", "tr": "Lütfen adınızı, telefonunuzu ve e-postanızı girin.", "ko": "이름, 전화번호, 이메일을 입력해 주세요.", "ja": "お名前、電話番号、メールアドレスを入力してください。",
  "vi": "Vui lòng điền tên, số điện thoại và email của bạn.", "fa": "لطفاً نام، تلفن و ایمیل خود را وارد کنید", "th": "โปรดกรอกชื่อ โทรศัพท์ และอีเมลของคุณ"
};

NOEL_I18N["form.flight_title_optional"] = {
  "en": "Add your flight number (optional)", "es": "Añade tu número de vuelo (opcional)", "fr": "Ajoutez votre numéro de vol (facultatif)", "ar": "أضف رقم رحلتك (اختياري)",
  "pt": "Adicione seu número de voo (opcional)", "ur": "Apna flight number likhen (optional)", "hi": "अपनी उड़ान संख्या जोड़ें (वैकल्पिक)", "bn": "আপনার ফ্লাইট নম্বর যোগ করুন (ঐচ্ছিক)",
  "ud": "اپنا فلائٹ نمبر شامل کریں (اختیاری)", "zh": "添加您的航班号（可选）", "de": "Flugnummer hinzufügen (optional)", "it": "Aggiungi il numero di volo (facoltativo)",
  "ru": "Добавить номер рейса (необязательно)", "tr": "Uçuş numaranızı ekleyin (isteğe bağlı)", "ko": "항공편 번호 추가(선택 사항)", "ja": "便名を追加（任意）",
  "vi": "Thêm số hiệu chuyến bay của bạn (tùy chọn)", "fa": "شمارهٔ پرواز خود را اضافه کنید (اختیاری)", "th": "เพิ่มหมายเลขเที่ยวบินของคุณ (ไม่บังคับ)"
};

NOEL_I18N["class.details_save_failed"] = {
  "en": "Your details could not be saved. Please try again.", "es": "No se pudieron guardar tus datos. Inténtalo de nuevo.", "fr": "Vos coordonnées n'ont pas pu être enregistrées. Veuillez réessayer.", "ar": "تعذّر حفظ بياناتك. يرجى المحاولة مرة أخرى.",
  "pt": "Seus dados não puderam ser salvos. Tente novamente.", "ur": "Aapki details save nahi ho saki. Please phir try karen.", "hi": "आपका विवरण सहेजा नहीं जा सका। कृपया पुनः प्रयास करें।", "bn": "আপনার বিবরণ সংরক্ষণ করা যায়নি। আবার চেষ্টা করুন।",
  "ud": "آپ کی تفصیلات محفوظ نہیں ہو سکیں، براہ کرم دوبارہ کوشش کریں", "zh": "无法保存您的信息。请重试。", "de": "Ihre Daten konnten nicht gespeichert werden. Bitte versuchen Sie es erneut.", "it": "Non è stato possibile salvare i tuoi dati. Riprova.",
  "ru": "Не удалось сохранить ваши данные. Пожалуйста, попробуйте снова.", "tr": "Bilgileriniz kaydedilemedi. Lütfen tekrar deneyin.", "ko": "정보를 저장할 수 없습니다. 다시 시도해 주세요.", "ja": "詳細を保存できませんでした。もう一度お試しください。",
  "vi": "Không thể lưu thông tin của bạn. Vui lòng thử lại.", "fa": "جزئیات شما ذخیره نشد، لطفاً دوباره تلاش کنید", "th": "ไม่สามารถบันทึกรายละเอียดของคุณได้ โปรดลองอีกครั้ง"
};

NOEL_I18N["form.something_wrong"] = {
  "en": "Something went wrong. Please try again.", "es": "Algo salió mal. Inténtalo de nuevo.", "fr": "Quelque chose s'est mal passé. Veuillez réessayer.", "ar": "حدث خطأ ما. يرجى المحاولة مرة أخرى.",
  "pt": "Algo deu errado. Tente novamente.", "ur": "Kuch ghalat ho gaya. Please phir try karen.", "hi": "कुछ ग़लत हो गया। कृपया पुनः प्रयास करें।", "bn": "কিছু ভুল হয়েছে। আবার চেষ্টা করুন।",
  "ud": "کچھ غلط ہوا، براہ کرم دوبارہ کوشش کریں", "zh": "出了点问题。请重试。", "de": "Etwas ist schiefgelaufen. Bitte versuchen Sie es erneut.", "it": "Qualcosa è andato storto. Riprova.",
  "ru": "Что-то пошло не так. Пожалуйста, попробуйте снова.", "tr": "Bir şeyler ters gitti. Lütfen tekrar deneyin.", "ko": "문제가 발생했습니다. 다시 시도해 주세요.", "ja": "問題が発生しました。もう一度お試しください。",
  "vi": "Đã xảy ra lỗi. Vui lòng thử lại.", "fa": "مشکلی پیش آمد، لطفاً دوباره تلاش کنید", "th": "เกิดข้อผิดพลาด โปรดลองอีกครั้ง"
};

NOEL_I18N["status.chat_empty"] = {
  "en": "No messages yet. Your chauffeur can read your messages here.", "es": "Aún no hay mensajes. Tu chófer puede leer tus mensajes aquí.", "fr": "Aucun message pour l'instant. Votre chauffeur peut lire vos messages ici.", "ar": "لا توجد رسائل بعد. يمكن لسائقك قراءة رسائلك هنا.",
  "pt": "Ainda não há mensagens. Seu motorista pode ler suas mensagens aqui.", "ur": "Abhi koi messages nahi hain. Aapka chauffeur aapke messages yahan padh sakta hai.", "hi": "अभी तक कोई संदेश नहीं है। आपका चालक आपके संदेश यहाँ पढ़ सकता है।", "bn": "এখনো কোনো বার্তা নেই। আপনার চালক আপনার বার্তা এখানে পড়তে পারবেন।",
  "ud": "ابھی کوئی پیغام نہیں ہے۔ آپ کا ڈرائیور آپ کا پیغام یہاں پڑھ سکتا ہے", "zh": "暂无消息。您的司机可以在此阅读您的消息。", "de": "Noch keine Nachrichten. Ihr Chauffeur kann Ihre Nachrichten hier lesen.", "it": "Ancora nessun messaggio. Il tuo chauffeur può leggere i tuoi messaggi qui.",
  "ru": "Пока нет сообщений. Ваш шофёр может читать ваши сообщения здесь.", "tr": "Henüz mesaj yok. Şoförünüz mesajlarınızı buradan okuyabilir.", "ko": "아직 메시지가 없습니다. 쇼퍼가 여기서 고객님의 메시지를 읽을 수 있습니다.", "ja": "まだメッセージがありません。ショファーはここでお客様のメッセージを読むことができます。",
  "vi": "Chưa có tin nhắn nào. Tài xế của bạn có thể đọc tin nhắn của bạn tại đây.", "fa": "هنوز پیامی نیست. رانندهٔ شما می‌تواند پیام شما را اینجا بخواند", "th": "ยังไม่มีข้อความ คนขับของคุณสามารถอ่านข้อความของคุณที่นี่"
};

NOEL_I18N["status.you"] = {
  "en": "You", "es": "Tú", "fr": "Vous", "ar": "أنت",
  "pt": "Você", "ur": "Aap", "hi": "आप", "bn": "আপনি",
  "ud": "آپ", "zh": "您", "de": "Sie", "it": "Tu",
  "ru": "Вы", "tr": "Siz", "ko": "고객님", "ja": "お客様",
  "vi": "Bạn", "fa": "شما", "th": "คุณ"
};

NOEL_I18N["status.chauffeur_word"] = {
  "en": "Chauffeur", "es": "Chófer", "fr": "Chauffeur", "ar": "السائق",
  "pt": "Motorista", "ur": "Chauffeur", "hi": "चालक", "bn": "চালক",
  "ud": "ڈرائیور", "zh": "司机", "de": "Chauffeur", "it": "Chauffeur",
  "ru": "Шофёр", "tr": "Şoför", "ko": "쇼퍼", "ja": "ショファー",
  "vi": "Tài xế", "fa": "راننده", "th": "คนขับ"
};

NOEL_I18N["status.pay_start_failed"] = {
  "en": "Could not start the secure payment form. Please try again.", "es": "No se pudo iniciar el formulario de pago seguro. Inténtalo de nuevo.", "fr": "Impossible de démarrer le formulaire de paiement sécurisé. Veuillez réessayer.", "ar": "تعذّر بدء نموذج الدفع الآمن. يرجى المحاولة مرة أخرى.",
  "pt": "Não foi possível iniciar o formulário de pagamento seguro. Tente novamente.", "ur": "Secure payment form start nahi ho saka. Please phir try karen.", "hi": "सुरक्षित भुगतान फ़ॉर्म शुरू नहीं हो सका। कृपया पुनः प्रयास करें।", "bn": "নিরাপদ পেমেন্ট ফর্ম শুরু করা যায়নি। আবার চেষ্টা করুন।",
  "ud": "محفوظ ادائیگی فارم شروع نہیں ہو سکا، براہ کرم دوبارہ کوشش کریں", "zh": "无法启动安全支付表单。请重试。", "de": "Das sichere Zahlungsformular konnte nicht gestartet werden. Bitte versuchen Sie es erneut.", "it": "Non è stato possibile avviare il modulo di pagamento sicuro. Riprova.",
  "ru": "Не удалось запустить форму безопасной оплаты. Пожалуйста, попробуйте снова.", "tr": "Güvenli ödeme formu başlatılamadı. Lütfen tekrar deneyin.", "ko": "안전 결제 양식을 시작할 수 없습니다. 다시 시도해 주세요.", "ja": "安全な決済フォームを開始できませんでした。もう一度お試しください。",
  "vi": "Không thể khởi động biểu mẫu thanh toán an toàn. Vui lòng thử lại.", "fa": "فرم پرداخت امن شروع نشد، لطفاً دوباره تلاش کنید", "th": "ไม่สามารถเริ่มแบบฟอร์มการชำระเงินที่ปลอดภัยได้ โปรดลองอีกครั้ง"
};

NOEL_I18N["status.remove"] = {
  "en": "Remove", "es": "Eliminar", "fr": "Supprimer", "ar": "إزالة",
  "pt": "Remover", "ur": "Remove", "hi": "हटाएँ", "bn": "সরান",
  "ud": "ہٹائیں", "zh": "删除", "de": "Entfernen", "it": "Rimuovi",
  "ru": "Удалить", "tr": "Kaldır", "ko": "삭제", "ja": "削除",
  "vi": "Xóa", "fa": "حذف", "th": "ลบ"
};

NOEL_I18N["status.remove_card_confirm"] = {
  "en": "Remove this saved card?", "es": "¿Eliminar esta tarjeta guardada?", "fr": "Supprimer cette carte enregistrée ?", "ar": "إزالة هذه البطاقة المحفوظة؟",
  "pt": "Remover este cartão salvo?", "ur": "Ye saved card remove kar den?", "hi": "क्या यह सहेजा गया कार्ड हटाएँ?", "bn": "এই সংরক্ষিত কার্ডটি সরাবেন?",
  "ud": "کیا آپ واقعی یہ محفوظ شدہ کارڈ ہٹانا چاہتے ہیں؟", "zh": "删除这张已保存的卡？", "de": "Diese gespeicherte Karte entfernen?", "it": "Rimuovere questa carta salvata?",
  "ru": "Удалить эту сохранённую карту?", "tr": "Bu kayıtlı kart kaldırılsın mı?", "ko": "이 저장된 카드를 삭제하시겠습니까?", "ja": "保存済みのこのカードを削除しますか？",
  "vi": "Xóa thẻ đã lưu này?", "fa": "آیا واقعاً می‌خواهید این کارت ذخیره‌شده را حذف کنید؟", "th": "ลบบัตรที่บันทึกไว้นี้หรือไม่?"
};

NOEL_I18N["status.remove_card_failed"] = {
  "en": "That card could not be removed.", "es": "No se pudo eliminar esa tarjeta.", "fr": "Cette carte n'a pas pu être supprimée.", "ar": "تعذّرت إزالة هذه البطاقة.",
  "pt": "Não foi possível remover esse cartão.", "ur": "Wo card remove nahi ho saka.", "hi": "वह कार्ड हटाया नहीं जा सका।", "bn": "ওই কার্ড সরানো যায়নি।",
  "ud": "یہ کارڈ ہٹایا نہیں جا سکا", "zh": "无法删除这张卡。", "de": "Diese Karte konnte nicht entfernt werden.", "it": "Non è stato possibile rimuovere questa carta.",
  "ru": "Не удалось удалить эту карту.", "tr": "Bu kart kaldırılamadı.", "ko": "이 카드를 삭제할 수 없습니다.", "ja": "このカードを削除できませんでした。",
  "vi": "Không thể xóa thẻ này.", "fa": "این کارت حذف نشد", "th": "ไม่สามารถลบบัตรนี้ได้"
};

NOEL_I18N["status.pay_confirm_missing"] = {
  "en": "Payment needs confirmation, but no confirmation was provided. Please try again.", "es": "El pago necesita confirmación, pero no se proporcionó ninguna. Inténtalo de nuevo.", "fr": "Le paiement nécessite une confirmation, mais aucune n'a été fournie. Veuillez réessayer.", "ar": "الدفع يحتاج إلى تأكيد، لكن لم يتم تقديم أي تأكيد. يرجى المحاولة مرة أخرى.",
  "pt": "O pagamento precisa de confirmação, mas nenhuma foi fornecida. Tente novamente.", "ur": "Payment ke liye confirmation chahiye, lekin koi confirmation nahi mili. Please phir try karen.", "hi": "भुगतान के लिए पुष्टि आवश्यक है, लेकिन कोई पुष्टि नहीं मिली। कृपया पुनः प्रयास करें।", "bn": "পেমেন্টের জন্য নিশ্চিতকরণ প্রয়োজন, কিন্তু কোনো নিশ্চিতকরণ দেওয়া হয়নি। আবার চেষ্টা করুন।",
  "ud": "ادائیگی کے لیے تصدیق درکار ہے لیکن کوئی تصدیق دستیاب نہیں ہے، براہ کرم دوبارہ کوشش کریں", "zh": "付款需要确认，但未提供确认信息。请重试。", "de": "Die Zahlung muss bestätigt werden, aber es wurde keine Bestätigung übermittelt. Bitte versuchen Sie es erneut.", "it": "Il pagamento richiede una conferma, ma non ne è stata fornita alcuna. Riprova.",
  "ru": "Платёж требует подтверждения, но подтверждение не было предоставлено. Пожалуйста, попробуйте снова.", "tr": "Ödeme onay gerektiriyor ancak onay sağlanmadı. Lütfen tekrar deneyin.", "ko": "결제 확인이 필요하지만 확인 정보가 제공되지 않았습니다. 다시 시도해 주세요.", "ja": "お支払いの確認が必要ですが、確認が提供されませんでした。もう一度お試しください。",
  "vi": "Thanh toán cần xác nhận, nhưng không có xác nhận nào được cung cấp. Vui lòng thử lại.", "fa": "پرداخت نیاز به تأیید دارد اما تأییدی در دسترس نیست، لطفاً دوباره تلاش کنید", "th": "การชำระเงินต้องการการยืนยัน แต่ไม่มีการยืนยันให้ โปรดลองอีกครั้ง"
};

NOEL_I18N["status.confirming"] = {
  "en": "Confirming…", "es": "Confirmando…", "fr": "Confirmation…", "ar": "جارٍ التأكيد…",
  "pt": "Confirmando…", "ur": "Confirm ho raha hai…", "hi": "पुष्टि हो रही है…", "bn": "নিশ্চিত করা হচ্ছে…",
  "ud": "تصدیق ہو رہی ہے…", "zh": "正在确认…", "de": "Bestätigung läuft…", "it": "Conferma in corso…",
  "ru": "Подтверждение…", "tr": "Onaylanıyor…", "ko": "확인 중…", "ja": "確認中…",
  "vi": "Đang xác nhận…", "fa": "در حال تأیید…", "th": "กำลังยืนยัน…"
};

NOEL_I18N["status.card_confirm_failed"] = {
  "en": "Your card could not be confirmed. Please try again.", "es": "No se pudo confirmar tu tarjeta. Inténtalo de nuevo.", "fr": "Votre carte n'a pas pu être confirmée. Veuillez réessayer.", "ar": "تعذّر تأكيد بطاقتك. يرجى المحاولة مرة أخرى.",
  "pt": "Seu cartão não pôde ser confirmado. Tente novamente.", "ur": "Aapka card confirm nahi ho saka. Please phir try karen.", "hi": "आपका कार्ड पुष्ट नहीं हो सका। कृपया पुनः प्रयास करें।", "bn": "আপনার কার্ড নিশ্চিত করা যায়নি। আবার চেষ্টা করুন।",
  "ud": "آپ کے کارڈ کی تصدیق نہیں ہو سکی، براہ کرم دوبارہ کوشش کریں", "zh": "无法确认您的卡。请重试。", "de": "Ihre Karte konnte nicht bestätigt werden. Bitte versuchen Sie es erneut.", "it": "Non è stato possibile confermare la tua carta. Riprova.",
  "ru": "Не удалось подтвердить вашу карту. Пожалуйста, попробуйте снова.", "tr": "Kartınız onaylanamadı. Lütfen tekrar deneyin.", "ko": "카드를 확인할 수 없습니다. 다시 시도해 주세요.", "ja": "カードを確認できませんでした。もう一度お試しください。",
  "vi": "Không thể xác nhận thẻ của bạn. Vui lòng thử lại.", "fa": "کارت شما تأیید نشد، لطفاً دوباره تلاش کنید", "th": "ไม่สามารถยืนยันบัตรของคุณได้ โปรดลองอีกครั้ง"
};

NOEL_I18N["status.processing"] = {
  "en": "Processing…", "es": "Procesando…", "fr": "Traitement…", "ar": "جارٍ المعالجة…",
  "pt": "Processando…", "ur": "Processing…", "hi": "प्रक्रिया चल रही है…", "bn": "প্রক্রিয়া চলছে…",
  "ud": "پروسیس ہو رہا ہے…", "zh": "正在处理…", "de": "Verarbeitung läuft…", "it": "Elaborazione in corso…",
  "ru": "Обработка…", "tr": "İşleniyor…", "ko": "처리 중…", "ja": "処理中…",
  "vi": "Đang xử lý…", "fa": "در حال پردازش…", "th": "กำลังดำเนินการ…"
};

NOEL_I18N["status.processing_test"] = {
  "en": "Processing (test mode)…", "es": "Procesando (modo de prueba)…", "fr": "Traitement (mode test)…", "ar": "جارٍ المعالجة (وضع الاختبار)…",
  "pt": "Processando (modo de teste)…", "ur": "Processing (test mode)…", "hi": "प्रक्रिया चल रही है (परीक्षण मोड)…", "bn": "প্রক্রিয়া চলছে (টেস্ট মোড)…",
  "ud": "پروسیس ہو رہا ہے (ٹیسٹ موڈ)…", "zh": "正在处理（测试模式）…", "de": "Verarbeitung läuft (Testmodus)…", "it": "Elaborazione in corso (modalità test)…",
  "ru": "Обработка (тестовый режим)…", "tr": "İşleniyor (test modu)…", "ko": "처리 중(테스트 모드)…", "ja": "処理中（テストモード）…",
  "vi": "Đang xử lý (chế độ thử nghiệm)…", "fa": "در حال پردازش (حالت آزمایشی)…", "th": "กำลังดำเนินการ (โหมดทดสอบ)…"
};

NOEL_I18N["status.pay_failed"] = {
  "en": "Payment could not be completed. Please try again.", "es": "No se pudo completar el pago. Inténtalo de nuevo.", "fr": "Le paiement n'a pas pu être effectué. Veuillez réessayer.", "ar": "تعذّر إتمام الدفع. يرجى المحاولة مرة أخرى.",
  "pt": "O pagamento não pôde ser concluído. Tente novamente.", "ur": "Payment complete nahi ho saka. Please phir try karen.", "hi": "भुगतान पूरा नहीं हो सका। कृपया पुनः प्रयास करें।", "bn": "পেমেন্ট সম্পন্ন করা যায়নি। আবার চেষ্টা করুন।",
  "ud": "ادائیگی مکمل نہیں ہو سکی، براہ کرم دوبارہ کوشش کریں", "zh": "无法完成付款。请重试。", "de": "Die Zahlung konnte nicht abgeschlossen werden. Bitte versuchen Sie es erneut.", "it": "Non è stato possibile completare il pagamento. Riprova.",
  "ru": "Не удалось завершить платёж. Пожалуйста, попробуйте снова.", "tr": "Ödeme tamamlanamadı. Lütfen tekrar deneyin.", "ko": "결제를 완료할 수 없습니다. 다시 시도해 주세요.", "ja": "お支払いを完了できませんでした。もう一度お試しください。",
  "vi": "Không thể hoàn tất thanh toán. Vui lòng thử lại.", "fa": "پرداخت تکمیل نشد، لطفاً دوباره تلاش کنید", "th": "ไม่สามารถดำเนินการชำระเงินให้เสร็จสิ้นได้ โปรดลองอีกครั้ง"
};

NOEL_I18N["status.pay_loading_wait"] = {
  "en": "The secure payment form is still loading. Please wait a moment and try again.", "es": "El formulario de pago seguro aún se está cargando. Espera un momento e inténtalo de nuevo.", "fr": "Le formulaire de paiement sécurisé est encore en cours de chargement. Veuillez patienter un instant et réessayer.", "ar": "نموذج الدفع الآمن ما زال يُحمَّل. يرجى الانتظار لحظة ثم المحاولة مرة أخرى.",
  "pt": "O formulário de pagamento seguro ainda está carregando. Aguarde um momento e tente novamente.", "ur": "Secure payment form abhi load ho raha hai. Please thoda wait karke phir try karen.", "hi": "सुरक्षित भुगतान फ़ॉर्म अभी भी लोड हो रहा है। कृपया थोड़ा प्रतीक्षा करें और पुनः प्रयास करें।", "bn": "নিরাপদ পেমেন্ট ফর্ম এখনো লোড হচ্ছে। একটু অপেক্ষা করে আবার চেষ্টা করুন।",
  "ud": "محفوظ ادائیگی فارم لوڈ ہو رہا ہے، براہ کرم تھوڑی دیر انتظار کریں اور دوبارہ کوشش کریں", "zh": "安全支付表单仍在加载中。请稍等片刻再试。", "de": "Das sichere Zahlungsformular lädt noch. Bitte warten Sie einen Moment und versuchen Sie es erneut.", "it": "Il modulo di pagamento sicuro è ancora in caricamento. Attendi un momento e riprova.",
  "ru": "Форма безопасной оплаты всё ещё загружается. Пожалуйста, подождите немного и попробуйте снова.", "tr": "Güvenli ödeme formu hâlâ yükleniyor. Lütfen biraz bekleyip tekrar deneyin.", "ko": "안전 결제 양식이 아직 로딩 중입니다. 잠시 기다렸다가 다시 시도해 주세요.", "ja": "安全な決済フォームはまだ読み込み中です。しばらく待ってからもう一度お試しください。",
  "vi": "Biểu mẫu thanh toán an toàn vẫn đang tải. Vui lòng đợi một lát và thử lại.", "fa": "فرم پرداخت امن در حال بارگذاری است، لطفاً کمی صبر کنید و دوباره تلاش کنید", "th": "แบบฟอร์มการชำระเงินที่ปลอดภัยกำลังโหลดอยู่ โปรดรอสักครู่แล้วลองอีกครั้ง"
};

NOEL_I18N["status.check_card"] = {
  "en": "Please check your card details and try again.", "es": "Revisa los datos de tu tarjeta e inténtalo de nuevo.", "fr": "Veuillez vérifier les coordonnées de votre carte et réessayer.", "ar": "يرجى التحقق من بيانات بطاقتك والمحاولة مرة أخرى.",
  "pt": "Verifique os dados do cartão e tente novamente.", "ur": "Please apne card ki details check karke phir try karen.", "hi": "कृपया अपने कार्ड का विवरण जाँचें और पुनः प्रयास करें।", "bn": "আপনার কার্ডের বিবরণ দেখে আবার চেষ্টা করুন।",
  "ud": "براہ کرم اپنے کارڈ کی تفصیلات چیک کریں اور دوبارہ کوشش کریں", "zh": "请检查您的卡信息并重试。", "de": "Bitte überprüfen Sie Ihre Kartendaten und versuchen Sie es erneut.", "it": "Controlla i dati della carta e riprova.",
  "ru": "Пожалуйста, проверьте данные вашей карты и попробуйте снова.", "tr": "Lütfen kart bilgilerinizi kontrol edip tekrar deneyin.", "ko": "카드 정보를 확인하고 다시 시도해 주세요.", "ja": "カード詳細を確認して、もう一度お試しください。",
  "vi": "Vui lòng kiểm tra chi tiết thẻ của bạn và thử lại.", "fa": "لطفاً جزئیات کارت خود را بررسی کنید و دوباره تلاش کنید", "th": "โปรดตรวจสอบรายละเอียดบัตรของคุณแล้วลองอีกครั้ง"
};

NOEL_I18N["status.cancel_failed"] = {
  "en": "Cancellation could not be completed.", "es": "No se pudo completar la cancelación.", "fr": "L'annulation n'a pas pu être effectuée.", "ar": "تعذّر إتمام الإلغاء.",
  "pt": "O cancelamento não pôde ser concluído.", "ur": "Cancellation complete nahi ho saki.", "hi": "रद्दीकरण पूरा नहीं हो सका।", "bn": "বাতিল সম্পন্ন করা যায়নি।",
  "ud": "منسوخی مکمل نہیں ہو سکی", "zh": "无法完成取消。", "de": "Die Stornierung konnte nicht abgeschlossen werden.", "it": "Non è stato possibile completare la cancellazione.",
  "ru": "Не удалось завершить отмену.", "tr": "İptal tamamlanamadı.", "ko": "취소를 완료할 수 없습니다.", "ja": "キャンセルを完了できませんでした。",
  "vi": "Không thể hoàn tất việc hủy.", "fa": "لغو تکمیل نشد", "th": "ไม่สามารถดำเนินการยกเลิกให้เสร็จสิ้นได้"
};

NOEL_I18N["status.pickup_prefix"] = {
  "en": " · Pickup: ", "es": " · Recogida: ", "fr": " · Prise en charge : ", "ar": " · الاستلام: ",
  "pt": " · Coleta: ", "ur": " · Pickup: ", "hi": " · पिकअप: ", "bn": " · পিকআপ: ",
  "ud": " · پک اپ: ", "zh": " · 上车：", "de": " · Abholung: ", "it": " · Ritiro: ",
  "ru": " · Подача: ", "tr": " · Biniş: ", "ko": " · 픽업: ", "ja": " · 乗車：",
  "vi": " · Đón: ", "fa": " · سوارشدن: ", "th": " · รับ: "
};

NOEL_I18N["status.reach_booking"] = {
  "en": "Could not reach the booking service. Please try again.", "es": "No se pudo contactar con el servicio de reservas. Inténtalo de nuevo.", "fr": "Impossible de joindre le service de réservation. Veuillez réessayer.", "ar": "تعذّر الوصول إلى خدمة الحجز. يرجى المحاولة مرة أخرى.",
  "pt": "Não foi possível acessar o serviço de reservas. Tente novamente.", "ur": "Booking service se connect nahi ho saka. Please phir try karen.", "hi": "बुकिंग सेवा से संपर्क नहीं हो सका। कृपया पुनः प्रयास करें।", "bn": "বুকিং পরিষেবায় পৌঁছানো যায়নি। আবার চেষ্টা করুন।",
  "ud": "بکنگ سروس تک نہیں پہنچا جا سکا، براہ کرم دوبارہ کوشش کریں", "zh": "无法连接到预订服务。请重试。", "de": "Der Buchungsdienst konnte nicht erreicht werden. Bitte versuchen Sie es erneut.", "it": "Non è stato possibile raggiungere il servizio di prenotazione. Riprova.",
  "ru": "Не удалось связаться со службой бронирования. Пожалуйста, попробуйте снова.", "tr": "Rezervasyon hizmetine ulaşılamadı. Lütfen tekrar deneyin.", "ko": "예약 서비스에 연결할 수 없습니다. 다시 시도해 주세요.", "ja": "予約サービスに接続できませんでした。もう一度お試しください。",
  "vi": "Không thể kết nối đến dịch vụ đặt xe. Vui lòng thử lại.", "fa": "نمی‌توان به سرویس رزرو رسید، لطفاً دوباره تلاش کنید", "th": "ไม่สามารถติดต่อบริการจองได้ โปรดลองอีกครั้ง"
};

NOEL_I18N["status.reach_payment"] = {
  "en": "Could not reach the payment service. Please try again.", "es": "No se pudo contactar con el servicio de pago. Inténtalo de nuevo.", "fr": "Impossible de joindre le service de paiement. Veuillez réessayer.", "ar": "تعذّر الوصول إلى خدمة الدفع. يرجى المحاولة مرة أخرى.",
  "pt": "Não foi possível acessar o serviço de pagamento. Tente novamente.", "ur": "Payment service se connect nahi ho saka. Please phir try karen.", "hi": "भुगतान सेवा से संपर्क नहीं हो सका। कृपया पुनः प्रयास करें।", "bn": "পেমেন্ট পরিষেবায় পৌঁছানো যায়নি। আবার চেষ্টা করুন।",
  "ud": "ادائیگی سروس تک نہیں پہنچا جا سکا، براہ کرم دوبارہ کوشش کریں", "zh": "无法连接到支付服务。请重试。", "de": "Der Zahlungsdienst konnte nicht erreicht werden. Bitte versuchen Sie es erneut.", "it": "Non è stato possibile raggiungere il servizio di pagamento. Riprova.",
  "ru": "Не удалось связаться с платёжной службой. Пожалуйста, попробуйте снова.", "tr": "Ödeme hizmetine ulaşılamadı. Lütfen tekrar deneyin.", "ko": "결제 서비스에 연결할 수 없습니다. 다시 시도해 주세요.", "ja": "決済サービスに接続できませんでした。もう一度お試しください。",
  "vi": "Không thể kết nối đến dịch vụ thanh toán. Vui lòng thử lại.", "fa": "نمی‌توان به سرویس پرداخت رسید، لطفاً دوباره تلاش کنید", "th": "ไม่สามารถติดต่อบริการชำระเงินได้ โปรดลองอีกครั้ง"
};

NOEL_I18N["status.reach_payment_check"] = {
  "en": "Could not reach the payment service. Please check your connection and try again.", "es": "No se pudo contactar con el servicio de pago. Revisa tu conexión e inténtalo de nuevo.", "fr": "Impossible de joindre le service de paiement. Veuillez vérifier votre connexion et réessayer.", "ar": "تعذّر الوصول إلى خدمة الدفع. يرجى التحقق من اتصالك والمحاولة مرة أخرى.",
  "pt": "Não foi possível acessar o serviço de pagamento. Verifique sua conexão e tente novamente.", "ur": "Payment service se connect nahi ho saka. Please apna connection check karke phir try karen.", "hi": "भुगतान सेवा से संपर्क नहीं हो सका। कृपया अपना कनेक्शन जाँचें और पुनः प्रयास करें।", "bn": "পেমেন্ট পরিষেবায় পৌঁছানো যায়নি। আপনার সংযোগ দেখে আবার চেষ্টা করুন।",
  "ud": "ادائیگی سروس تک نہیں پہنچا جا سکا، براہ کرم اپنا کنکشن چیک کریں اور دوبارہ کوشش کریں", "zh": "无法连接到支付服务。请检查您的网络连接并重试。", "de": "Der Zahlungsdienst konnte nicht erreicht werden. Bitte überprüfen Sie Ihre Verbindung und versuchen Sie es erneut.", "it": "Non è stato possibile raggiungere il servizio di pagamento. Controlla la connessione e riprova.",
  "ru": "Не удалось связаться с платёжной службой. Пожалуйста, проверьте соединение и попробуйте снова.", "tr": "Ödeme hizmetine ulaşılamadı. Lütfen bağlantınızı kontrol edip tekrar deneyin.", "ko": "결제 서비스에 연결할 수 없습니다. 연결을 확인한 뒤 다시 시도해 주세요.", "ja": "決済サービスに接続できませんでした。接続を確認して、もう一度お試しください。",
  "vi": "Không thể kết nối đến dịch vụ thanh toán. Vui lòng kiểm tra kết nối của bạn và thử lại.", "fa": "نمی‌توان به سرویس پرداخت رسید، لطفاً اتصال خود را بررسی کنید و دوباره تلاش کنید", "th": "ไม่สามารถติดต่อบริการชำระเงินได้ โปรดตรวจสอบการเชื่อมต่อของคุณแล้วลองอีกครั้ง"
};

NOEL_I18N["status.view_ride"] = {
  "en": "View this ride", "es": "Ver este viaje", "fr": "Voir ce trajet", "ar": "عرض هذه الرحلة",
  "pt": "Ver esta viagem", "ur": "Ye ride dekhen", "hi": "यह सवारी देखें", "bn": "এই রাইড দেখুন",
  "ud": "یہ سواری دیکھیں", "zh": "查看此行程", "de": "Diese Fahrt ansehen", "it": "Vedi questa corsa",
  "ru": "Посмотреть эту поездку", "tr": "Bu yolculuğu görüntüle", "ko": "이 이동 보기", "ja": "この乗車を見る",
  "vi": "Xem chuyến đi này", "fa": "مشاهدهٔ این سفر", "th": "ดูการเดินทางนี้"
};

NOEL_I18N["status.lookup_failed_email"] = {
  "en": "Could not look up rides for that email.", "es": "No se pudieron buscar viajes para ese correo.", "fr": "Impossible de rechercher des trajets pour cet e-mail.", "ar": "تعذّر البحث عن رحلات لهذا البريد الإلكتروني.",
  "pt": "Não foi possível buscar viagens para esse e-mail.", "ur": "Is email ke liye rides nahi mil saki.", "hi": "उस ईमेल के लिए सवारियाँ नहीं मिल सकीं।", "bn": "ওই ইমেইলের জন্য রাইড খুঁজে পাওয়া যায়নি।",
  "ud": "اس ای میل کے لیے کوئی سواری نہیں ملی", "zh": "无法查找该邮箱的行程。", "de": "Fahrten für diese E-Mail-Adresse konnten nicht gesucht werden.", "it": "Non è stato possibile cercare le corse per questa email.",
  "ru": "Не удалось найти поездки для этой электронной почты.", "tr": "Bu e-posta için yolculuk bulunamadı.", "ko": "해당 이메일의 이동을 찾을 수 없습니다.", "ja": "そのメールの乗車を検索できませんでした。",
  "vi": "Không thể tra cứu chuyến đi cho email đó.", "fa": "برای آن ایمیل سفری یافت نشد", "th": "ไม่สามารถค้นหาการเดินทางสำหรับอีเมลนั้นได้"
};

NOEL_I18N["status.flight_prefix"] = {
  "en": "Flight: ", "es": "Vuelo: ", "fr": "Vol : ", "ar": "الرحلة: ",
  "pt": "Voo: ", "ur": "Flight: ", "hi": "उड़ान: ", "bn": "ফ্লাইট: ",
  "ud": "فلائٹ: ", "zh": "航班：", "de": "Flug: ", "it": "Volo: ",
  "ru": "Рейс: ", "tr": "Uçuş: ", "ko": "항공편: ", "ja": "便：",
  "vi": "Chuyến bay: ", "fa": "پرواز: ", "th": "เที่ยวบิน: "
};

NOEL_I18N["status.chauffeur_prefix"] = {
  "en": "Chauffeur: ", "es": "Chófer: ", "fr": "Chauffeur : ", "ar": "السائق: ",
  "pt": "Motorista: ", "ur": "Chauffeur: ", "hi": "चालक: ", "bn": "চালক: ",
  "ud": "ڈرائیور: ", "zh": "司机：", "de": "Chauffeur: ", "it": "Chauffeur: ",
  "ru": "Шофёр: ", "tr": "Şoför: ", "ko": "쇼퍼: ", "ja": "ショファー：",
  "vi": "Tài xế: ", "fa": "راننده: ", "th": "คนขับ: "
};

NOEL_I18N["form.prev_month"] = {
  "en": "Previous month", "es": "Mes anterior", "fr": "Mois précédent", "ar": "الشهر السابق",
  "pt": "Mês anterior", "ur": "Pichla month", "hi": "पिछला महीना", "bn": "আগের মাস",
  "ud": "پچھلا مہینہ", "zh": "上个月", "de": "Vorheriger Monat", "it": "Mese precedente",
  "ru": "Предыдущий месяц", "tr": "Önceki ay", "ko": "이전 달", "ja": "先月",
  "vi": "Tháng trước", "fa": "ماه قبل", "th": "เดือนก่อน"
};

NOEL_I18N["form.next_month"] = {
  "en": "Next month", "es": "Mes siguiente", "fr": "Mois suivant", "ar": "الشهر التالي",
  "pt": "Próximo mês", "ur": "Agla month", "hi": "अगला महीना", "bn": "পরের মাস",
  "ud": "اگلا مہینہ", "zh": "下个月", "de": "Nächster Monat", "it": "Mese successivo",
  "ru": "Следующий месяц", "tr": "Sonraki ay", "ko": "다음 달", "ja": "来月",
  "vi": "Tháng tới", "fa": "ماه بعد", "th": "เดือนหน้า"
};

NOEL_I18N["status.your_pickup_point"] = {
  "en": "your pickup point", "es": "tu punto de recogida", "fr": "votre point de prise en charge", "ar": "نقطة الاستلام الخاصة بك",
  "pt": "seu ponto de coleta", "ur": "aapka pickup point", "hi": "आपका पिकअप पॉइंट", "bn": "আপনার পিকআপ পয়েন্ট",
  "ud": "آپ کا پک اپ پوائنٹ", "zh": "您的上车点", "de": "Ihrem Abholort", "it": "il tuo punto di partenza",
  "ru": "ваша точка подачи", "tr": "biniş noktanız", "ko": "픽업 지점", "ja": "お客様の乗車地点",
  "vi": "điểm đón của bạn", "fa": "نقطهٔ سوارشدن شما", "th": "จุดรับของคุณ"
};

NOEL_I18N["status.cancel_confirm_app"] = {
  "en": "Cancel this booking? The cancellation rules apply.", "es": "¿Cancelar esta reserva? Se aplican las reglas de cancelación.", "fr": "Annuler cette réservation ? Les règles d'annulation s'appliquent.", "ar": "إلغاء هذا الحجز؟ تنطبق قواعد الإلغاء.",
  "pt": "Cancelar esta reserva? As regras de cancelamento se aplicam.", "ur": "Ye booking cancel kar den? Cancellation rules apply honge.", "hi": "क्या यह बुकिंग रद्द करें? रद्दीकरण के नियम लागू होंगे।", "bn": "এই বুকিং বাতিল করবেন? বাতিলের নিয়ম প্রযোজ্য হবে।",
  "ud": "کیا آپ واقعی یہ بکنگ منسوخ کرنا چاہتے ہیں؟ منسوخی کے اصول لاگو ہوتے ہیں", "zh": "取消此预订？取消规则适用。", "de": "Diese Buchung stornieren? Es gelten die Stornierungsbedingungen.", "it": "Annullare questa prenotazione? Si applicano le regole di cancellazione.",
  "ru": "Отменить это бронирование? Применяются правила отмены.", "tr": "Bu rezervasyonu iptal etmek istiyor musunuz? İptal kuralları geçerlidir.", "ko": "이 예약을 취소하시겠습니까? 취소 규정이 적용됩니다.", "ja": "この予約をキャンセルしますか？キャンセル規定が適用されます。",
  "vi": "Hủy đặt xe này? Áp dụng quy định hủy xe.", "fa": "آیا واقعاً می‌خواهید این رزرو را لغو کنید؟ قوانین لغو اعمال می‌شود", "th": "ยกเลิกการจองนี้หรือไม่? กฎการยกเลิกมีผลบังคับใช้"
};

NOEL_I18N["class.hl0_caption"] = {
  "en": "Clean, quiet, and executive-level comfort.", "es": "Comodidad limpia, tranquila y de nivel ejecutivo.", "fr": "Un confort propre, calme et de niveau exécutif.", "ar": "راحة نظيفة وهادئة بمستوى تنفيذي.",
  "pt": "Conforto limpo, silencioso e de nível executivo.", "ur": "Clean, quiet, aur executive-level comfort.", "hi": "स्वच्छ, शांत और कार्यकारी स्तर का आराम।", "bn": "পরিষ্কার, শান্ত ও এক্সিকিউটিভ মানের আরাম।",
  "ud": "صاف ستھری، پرسکون اور ایگزیکٹو سطح کا آرام", "zh": "干净、安静、高管级舒适。", "de": "Sauber, ruhig und Komfort auf Executive-Niveau.", "it": "Pulito, silenzioso e comfort di livello executive.",
  "ru": "Чисто, тихо и комфорт уровня executive.", "tr": "Temiz, sessiz ve yönetici düzeyinde konfor.", "ko": "깨끗하고 조용하며 임원급 편안함.", "ja": "清潔で静か、エグゼクティブレベルの快適さ。",
  "vi": "Sạch sẽ, yên tĩnh và thoải mái ở đẳng cấp điều hành.", "fa": "تمیز، آرام و راحتی در سطح اجرایی", "th": "สะอาด เงียบ และสะดวกสบายระดับผู้บริหาร"
};

NOEL_I18N["class.hl1_title"] = {
  "en": "Professional chauffeurs", "es": "Chóferes profesionales", "fr": "Chauffeurs professionnels", "ar": "سائقون محترفون",
  "pt": "Motoristas profissionais", "ur": "Professional chauffeurs", "hi": "पेशेवर चालक", "bn": "পেশাদার চালক",
  "ud": "پیشہ ور ڈرائیور", "zh": "专业司机", "de": "Professionelle Chauffeure", "it": "Chauffeur professionisti",
  "ru": "Профессиональные шофёры", "tr": "Profesyonel şoförler", "ko": "전문 쇼퍼", "ja": "プロのショファー",
  "vi": "Tài xế chuyên nghiệp", "fa": "رانندهٔ حرفه‌ای", "th": "คนขับมืออาชีพ"
};

NOEL_I18N["class.hl1_text"] = {
  "en": "Polite, experienced chauffeurs who know the roads and respect your time.", "es": "Chóferes educados y experimentados que conocen las carreteras y respetan tu tiempo.", "fr": "Des chauffeurs polis et expérimentés qui connaissent les routes et respectent votre temps.", "ar": "سائقون مهذبون وذوو خبرة يعرفون الطرق ويحترمون وقتك.",
  "pt": "Motoristas educados e experientes que conhecem as estradas e respeitam seu tempo.", "ur": "Polite, experienced chauffeurs jo roads jaante hain aur aapke time ki izzat karte hain.", "hi": "विनम्र, अनुभवी चालक जो सड़कों को जानते हैं और आपके समय का सम्मान करते हैं।", "bn": "ভদ্র, অভিজ্ঞ চালক যারা রাস্তা জানেন এবং আপনার সময়কে সম্মান করেন।",
  "ud": "شائستہ، تجربہ کار ڈرائیور جو سڑکیں جانتا ہے اور آپ کے وقت کی قدر کرتا ہے", "zh": "礼貌、经验丰富的司机，熟悉路况并尊重您的时间。", "de": "Höfliche, erfahrene Chauffeure, die die Straßen kennen und Ihre Zeit respektieren.", "it": "Chauffeur educati ed esperti, che conoscono le strade e rispettano il tuo tempo.",
  "ru": "Вежливые, опытные шофёры, которые знают дороги и уважают ваше время.", "tr": "Yolları bilen ve zamanınıza saygı duyan kibar, deneyimli şoförler.", "ko": "도로를 잘 알고 고객님의 시간을 존중하는 정중하고 경험 많은 쇼퍼.", "ja": "道路を熟知し、お客様の時間を尊重する礼儀正しく経験豊富なショファー。",
  "vi": "Tài xế lịch sự, giàu kinh nghiệm, am hiểu đường sá và tôn trọng thời gian của bạn.", "fa": "رانندهٔ مؤدب و باتجربه که جاده‌ها را می‌شناسد و به وقت شما احترام می‌گذارد", "th": "คนขับสุภาพ มีประสบการณ์ รู้จักถนนและเคารพเวลาของคุณ"
};

NOEL_I18N["class.hl2_title"] = {
  "en": "On-time pickups", "es": "Recogidas puntuales", "fr": "Prises en charge ponctuelles", "ar": "استلام في الوقت المحدد",
  "pt": "Coletas pontuais", "ur": "On-time pickups", "hi": "समय पर पिकअप", "bn": "সময়মতো পিকআপ",
  "ud": "وقت پر پک اپ", "zh": "准时接送", "de": "Pünktliche Abholungen", "it": "Ritiri puntuali",
  "ru": "Пунктуальная подача", "tr": "Zamanında biniş", "ko": "정시 픽업", "ja": "時間通りの乗車",
  "vi": "Đón đúng giờ", "fa": "سوارشدن سر وقت", "th": "รับตรงเวลา"
};

NOEL_I18N["class.hl2_text"] = {
  "en": "Your chauffeur plans the route and arrives on time, every time.", "es": "Tu chófer planifica la ruta y llega a tiempo, siempre.", "fr": "Votre chauffeur planifie l'itinéraire et arrive à l'heure, à chaque fois.", "ar": "سائقك يخطط للطريق ويصل في الوقت المحدد، في كل مرة.",
  "pt": "Seu motorista planeja a rota e chega na hora, sempre.", "ur": "Aapka chauffeur route plan karta hai aur har baar time par pahunchta hai.", "hi": "आपका चालक मार्ग की योजना बनाता है और हर बार समय पर पहुँचता है।", "bn": "আপনার চালক রুট পরিকল্পনা করেন এবং প্রতিবার সময়মতো পৌঁছান।",
  "ud": "آپ کا ڈرائیور راستہ منصوبہ بندی کرتا ہے اور ہر بار وقت پر پہنچتا ہے", "zh": "您的司机会规划路线，每次都准时到达。", "de": "Ihr Chauffeur plant die Route und kommt jedes Mal pünktlich an.", "it": "Il tuo chauffeur pianifica il percorso e arriva in orario, ogni volta.",
  "ru": "Ваш шофёр планирует маршрут и всегда приезжает вовремя.", "tr": "Şoförünüz rotayı planlar ve her seferinde zamanında varır.", "ko": "쇼퍼가 경로를 계획하고 매번 정시에 도착합니다.", "ja": "ショファーがルートを計画し、毎回時間通りに到着します。",
  "vi": "Tài xế của bạn lên kế hoạch lộ trình và đến đúng giờ, mọi lúc.", "fa": "رانندهٔ شما مسیر را برنامه‌ریزی می‌کند و هر بار سر وقت می‌رسد", "th": "คนขับของคุณวางแผนเส้นทางและมาถึงตรงเวลาทุกครั้ง"
};

NOEL_I18N["class.hl3_title"] = {
  "en": "Recent high-end cars", "es": "Coches recientes de alta gama", "fr": "Voitures récentes haut de gamme", "ar": "سيارات حديثة فاخرة",
  "pt": "Carros recentes de alto padrão", "ur": "Recent high-end cars", "hi": "हाल की उच्च-स्तरीय कारें", "bn": "সাম্প্রতিক উচ্চমানের গাড়ি",
  "ud": "نئی لگژری گاڑیاں", "zh": "较新的高端车辆", "de": "Neueste hochwertige Autos", "it": "Auto recenti di fascia alta",
  "ru": "Новые автомобили высокого класса", "tr": "Yeni üst sınıf araçlar", "ko": "최신 고급 차량", "ja": "最新のハイエンド車",
  "vi": "Xe cao cấp đời mới", "fa": "خودروهای لوکس جدید", "th": "รถยนต์ระดับสูงรุ่นใหม่"
};

NOEL_I18N["class.hl3_text"] = {
  "en": "Clean, comfortable, recent cars, ready for every ride.", "es": "Coches limpios, cómodos y recientes, listos para cada viaje.", "fr": "Des voitures propres, confortables et récentes, prêtes pour chaque trajet.", "ar": "سيارات نظيفة ومريحة وحديثة، جاهزة لكل رحلة.",
  "pt": "Carros limpos, confortáveis e recentes, prontos para cada viagem.", "ur": "Clean, comfortable, recent cars, har ride ke liye ready.", "hi": "स्वच्छ, आरामदायक, हाल की कारें, हर सवारी के लिए तैयार।", "bn": "পরিষ্কার, আরামদায়ক, সাম্প্রতিক গাড়ি, প্রতিটি রাইডের জন্য প্রস্তুত।",
  "ud": "صاف ستھری، آرام دہ، نئی لگژری گاڑیاں، ہر سواری کے لیے تیار", "zh": "干净、舒适、较新的车辆，随时为每次行程做好准备。", "de": "Saubere, komfortable, neuere Autos, bereit für jede Fahrt.", "it": "Auto pulite, confortevoli e recenti, pronte per ogni corsa.",
  "ru": "Чистые, комфортабельные, новые автомобили, готовые к любой поездке.", "tr": "Temiz, konforlu, yeni araçlar, her yolculuğa hazır.", "ko": "깨끗하고 편안한 최신 차량으로 모든 이동에 대비되어 있습니다.", "ja": "清潔で快適な最新車両、あらゆる乗車に対応可能。",
  "vi": "Xe sạch sẽ, thoải mái, đời mới, sẵn sàng cho mọi chuyến đi.", "fa": "خودروهای لوکس تمیز، راحت و جدید، آماده برای هر سفر", "th": "รถยนต์สะอาด สะดวกสบาย รุ่นใหม่ พร้อมสำหรับการเดินทางทุกครั้ง"
};

NOEL_I18N["class.hl4_title"] = {
  "en": "Arrive fully charged", "es": "Llega con la batería llena", "fr": "Arrivez avec le téléphone chargé", "ar": "صِل وهاتفك مشحون بالكامل",
  "pt": "Chegue com a bateria cheia", "ur": "Arrive fully charged", "hi": "पूरी तरह चार्ज होकर पहुँचें", "bn": "পুরো চার্জ নিয়ে পৌঁছান",
  "ud": "فون چارج شدہ حالت میں پہنچیں", "zh": "到达时手机充满电", "de": "Kommen Sie mit vollem Akku an", "it": "Arriva con il telefono carico",
  "ru": "Приезжайте с полностью заряженным телефоном", "tr": "Telefonunuz dolu olarak varın", "ko": "휴대폰 충전 완료 상태로 도착", "ja": "電話をフル充電で到着",
  "vi": "Đến nơi với điện thoại đầy pin", "fa": "با تلفن شارژشده برسید", "th": "ถึงที่หมายพร้อมโทรศัพท์เต็ม"
};

NOEL_I18N["class.hl4_text"] = {
  "en": "Phone chargers in every car, so your phone is full when you arrive.", "es": "Cargadores de teléfono en cada coche, para que tu teléfono esté lleno al llegar.", "fr": "Des chargeurs de téléphone dans chaque voiture, pour que votre téléphone soit chargé à l'arrivée.", "ar": "شواحن هواتف في كل سيارة، ليكون هاتفك مشحونًا بالكامل عند وصولك.",
  "pt": "Carregadores de telefone em cada carro, para que seu telefone esteja cheio ao chegar.", "ur": "Har gaari mein phone chargers, taaki aapke pahunchne par aapka phone full ho.", "hi": "हर कार में फ़ोन चार्जर, ताकि आपके पहुँचने पर आपका फ़ोन पूरा चार्ज हो।", "bn": "প্রতিটি গাড়িতে ফোন চার্জার, যাতে পৌঁছানোর সময় আপনার ফোন পুরো চার্জ থাকে।",
  "ud": "ہر گاڑی میں فون چارجر موجود ہے تاکہ آپ منزل پر پہنچیں تو فون چارج شدہ ہو", "zh": "每辆车都配有手机充电器，到达时您的手机将充满电。", "de": "Handyladegeräte in jedem Auto, damit Ihr Telefon bei der Ankunft voll aufgeladen ist.", "it": "Caricabatterie in ogni auto, così il telefono è carico all'arrivo.",
  "ru": "Зарядные устройства в каждом автомобиле, чтобы ваш телефон был полностью заряжен по прибытии.", "tr": "Her araçta telefon şarj cihazları var, böylece vardığınızda telefonunuz dolu olur.", "ko": "모든 차량에 휴대폰 충전기가 있어 도착 시 휴대폰이 완전히 충전되어 있습니다.", "ja": "すべての車に電話充電器があり、到着時には電話がフル充電されています。",
  "vi": "Bộ sạc điện thoại trên mọi xe, vì vậy điện thoại của bạn sẽ đầy pin khi đến nơi.", "fa": "در هر خودرو شارژر تلفن هست تا با تلفن شارژشده به مقصد برسید", "th": "ที่ชาร์จโทรศัพท์ในรถทุกคัน เพื่อให้โทรศัพท์ของคุณเต็มเมื่อถึงที่หมาย"
};

(function () {
  "use strict";

  var LANGS = [
    { code: "en", label: "English (US)", native: "English (US)", dir: "ltr" },
    { code: "es", label: "Spanish", native: "Español", dir: "ltr" },
    { code: "fr", label: "French", native: "Français", dir: "ltr" },
    { code: "ar", label: "Arabic", native: "العربية", dir: "rtl" },
    { code: "pt", label: "Portuguese", native: "Português", dir: "ltr" },
    { code: "ur", label: "Roman Urdu", native: "Roman Urdu", dir: "ltr" },
    { code: "hi", label: "Hindi", native: "हिन्दी", dir: "ltr" },
    { code: "bn", label: "Bengali", native: "বাংলা", dir: "ltr" },
    { code: "ud", label: "Urdu", native: "اردو", dir: "rtl" },
    { code: "zh", label: "Chinese Simplified", native: "简体中文", dir: "ltr" },
    { code: "de", label: "German", native: "Deutsch", dir: "ltr" },
    { code: "it", label: "Italian", native: "Italiano", dir: "ltr" },
    { code: "ru", label: "Russian", native: "Русский", dir: "ltr" },
    { code: "tr", label: "Turkish", native: "Türkçe", dir: "ltr" },
    { code: "ko", label: "Korean", native: "한국어", dir: "ltr" },
    { code: "ja", label: "Japanese", native: "日本語", dir: "ltr" },
    { code: "vi", label: "Vietnamese", native: "Tiếng Việt", dir: "ltr" },
    { code: "fa", label: "Persian", native: "فارسی", dir: "rtl" },
    { code: "th", label: "Thai", native: "ไทย", dir: "ltr" },
  ];
  var STORAGE_KEY = "noel-language";
  var DEFAULT_LANG = "en";

  function langEntry(code) {
    for (var i = 0; i < LANGS.length; i++) {
      if (LANGS[i].code === code) return LANGS[i];
    }
    return LANGS[0];
  }

  function storedLang() {
    try {
      var v = window.localStorage.getItem(STORAGE_KEY);
      if (v) return langEntry(v).code;
    } catch (e) { /* storage unavailable (private mode) — fall back */ }
    return DEFAULT_LANG;
  }

  function current() { return storedLang(); }

  function t(key, vars) {
    var dict = window.NOEL_I18N || {};
    var entry = dict[key];
    var s = entry ? (entry[current()] || entry.en || key) : key;
    if (vars) {
      for (var k in vars) {
        if (Object.prototype.hasOwnProperty.call(vars, k)) {
          s = s.split("{" + k + "}").join(String(vars[k]));
        }
      }
    }
    return s;
  }

  function applyToStaticText() {
    var els = document.querySelectorAll("[data-i18n]");
    for (var i = 0; i < els.length; i++) {
      els[i].textContent = t(els[i].getAttribute("data-i18n"));
    }
    var phs = document.querySelectorAll("[data-i18n-ph]");
    for (var j = 0; j < phs.length; j++) {
      phs[j].setAttribute("placeholder", t(phs[j].getAttribute("data-i18n-ph")));
    }
    var arias = document.querySelectorAll("[data-i18n-aria]");
    for (var k = 0; k < arias.length; k++) {
      arias[k].setAttribute("aria-label", t(arias[k].getAttribute("data-i18n-aria")));
    }
  }

  function applyLanguage(code, opts) {
    var entry = langEntry(code);
    try { window.localStorage.setItem(STORAGE_KEY, entry.code); } catch (e) { /* ignore */ }
    document.documentElement.setAttribute("lang", entry.code);
    document.documentElement.setAttribute("dir", entry.dir);
    document.documentElement.classList.toggle("noel-rtl", entry.dir === "rtl");
    applyToStaticText();
    updatePickerLabels();
    if (!opts || !opts.silent) {
      var ev;
      try {
        ev = new CustomEvent("noel-language-changed", { detail: { lang: entry.code, dir: entry.dir } });
      } catch (e) {
        ev = document.createEvent("Event");
        ev.initEvent("noel-language-changed", true, true);
        ev.detail = { lang: entry.code, dir: entry.dir };
      }
      document.dispatchEvent(ev);
    }
  }

  /* ---- Picker dropdown (shared markup builder, used by website menu + /app header) ---- */
  function buildPicker(container, buttonLabelEl) {
    var wrap = document.createElement("div");
    wrap.className = "noel-lang-picker";
    var btn = document.createElement("button");
    btn.type = "button";
    btn.className = "noel-lang-btn";
    btn.setAttribute("aria-haspopup", "listbox");
    btn.setAttribute("aria-expanded", "false");
    var btnLabel = document.createElement("span");
    btnLabel.className = "noel-lang-btn-label";
    btnLabel.textContent = langEntry(current()).native;
    btn.appendChild(btnLabel);
    var caret = document.createElement("span");
    caret.className = "noel-lang-caret";
    caret.setAttribute("aria-hidden", "true");
    caret.textContent = "▾";
    btn.appendChild(caret);
    var dd = document.createElement("div");
    dd.className = "noel-lang-dropdown";
    dd.setAttribute("role", "listbox");
    dd.hidden = true;
    var search = document.createElement("input");
    search.type = "text";
    search.className = "noel-lang-search";
    search.setAttribute("placeholder", t("app.search_language"));
    search.setAttribute("aria-label", t("app.search_language"));
    search.setAttribute("autocomplete", "off");
    dd.appendChild(search);
    var list = document.createElement("div");
    list.className = "noel-lang-list";
    dd.appendChild(list);

    function renderList(filter) {
      list.innerHTML = "";
      var q = (filter || "").trim().toLowerCase();
      var shown = 0;
      LANGS.forEach(function (l) {
        var hay = (l.label + " " + l.native + " " + l.code).toLowerCase();
        if (q && hay.indexOf(q) === -1) return;
        shown++;
        var item = document.createElement("button");
        item.type = "button";
        item.className = "noel-lang-item" + (l.code === current() ? " is-selected" : "");
        item.setAttribute("role", "option");
        item.setAttribute("aria-selected", l.code === current() ? "true" : "false");
        item.setAttribute("data-lang", l.code);
        var native = document.createElement("span");
        native.className = "noel-lang-native";
        native.textContent = l.native;
        var eng = document.createElement("span");
        eng.className = "noel-lang-eng";
        eng.textContent = l.label;
        item.appendChild(native);
        item.appendChild(eng);
        if (l.code === current()) {
          var tick = document.createElement("span");
          tick.className = "noel-lang-check";
          tick.setAttribute("aria-hidden", "true");
          tick.textContent = "✓";
          item.appendChild(tick);
        }
        item.addEventListener("click", function () {
          applyLanguage(l.code);
          closeDropdown();
        });
        list.appendChild(item);
      });
      if (!shown) {
        var empty = document.createElement("div");
        empty.className = "noel-lang-empty";
        empty.textContent = t("lang.no_results");
        list.appendChild(empty);
      }
    }

    function openDropdown() {
      dd.hidden = false;
      btn.setAttribute("aria-expanded", "true");
      renderList(search.value);
      search.focus();
    }
    function closeDropdown() {
      dd.hidden = true;
      btn.setAttribute("aria-expanded", "false");
    }
    btn.addEventListener("click", function (e) {
      e.stopPropagation();
      if (dd.hidden) { openDropdown(); } else { closeDropdown(); }
    });
    search.addEventListener("input", function () { renderList(search.value); });
    search.addEventListener("keydown", function (e) {
      if (e.key === "Escape") { closeDropdown(); btn.focus(); }
    });
    document.addEventListener("click", function (e) {
      if (!wrap.contains(e.target)) closeDropdown();
    });
    document.addEventListener("keydown", function (e) {
      if (e.key === "Escape") closeDropdown();
    });
    wrap.appendChild(btn);
    wrap.appendChild(dd);
    container.appendChild(wrap);
    renderList("");
    return { wrap: wrap, button: btn, close: closeDropdown };
  }

  function updatePickerLabels() {
    var labels = document.querySelectorAll(".noel-lang-btn-label");
    for (var i = 0; i < labels.length; i++) {
      labels[i].textContent = langEntry(current()).native;
    }
    var searches = document.querySelectorAll(".noel-lang-search");
    for (var j = 0; j < searches.length; j++) {
      searches[j].setAttribute("placeholder", t("app.search_language"));
      searches[j].setAttribute("aria-label", t("app.search_language"));
    }
  }

  window.NoelI18n = {
    LANGS: LANGS,
    STORAGE_KEY: STORAGE_KEY,
    current: current,
    set: function (code) { applyLanguage(code); },
    t: t,
    apply: applyLanguage,
    buildPicker: buildPicker,
    /* Calendar names for the current language (months_full /
       months_short / days_short), or null when i18n.js has no
       calendar table — callers fall back to English. */
    cal: function (kind) {
      try {
        var table = window.NOEL_CAL && window.NOEL_CAL[kind];
        if (table && table[current()]) return table[current()];
        if (table && table.en) return table.en;
      } catch (e) { /* fall through */ }
      return null;
    }
  };

  /* Apply the stored language as early as possible. The <html> lang/dir
     flip happens immediately (documentElement exists while <head> is still
     parsing, so a returning Arabic user never sees a left-to-right flash);
     the text rewrite runs again once the DOM is ready, when the elements
     exist. Both calls are idempotent and silent (no change event). */
  applyLanguage(current(), { silent: true });
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", function () { applyLanguage(current(), { silent: true }); });
  }
})();

/* Calendar month / weekday names, by site language. Roman Urdu uses the
   English month and day names, as spoken. Arabic uses full day names
   (abbreviations are not standard in Arabic). The date pickers read
   these through NoelI18n.cal(kind) so a language switch repaints the
   calendar; without i18n.js the pickers fall back to English. */
window.NOEL_CAL = {
  months_full: {
    en: ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"],
    es: ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"],
    fr: ["janvier", "février", "mars", "avril", "mai", "juin", "juillet", "août", "septembre", "octobre", "novembre", "décembre"],
    ar: ["يناير", "فبراير", "مارس", "أبريل", "مايو", "يونيو", "يوليو", "أغسطس", "سبتمبر", "أكتوبر", "نوفمبر", "ديسمبر"],
    pt: ["janeiro", "fevereiro", "março", "abril", "maio", "junho", "julho", "agosto", "setembro", "outubro", "novembro", "dezembro"],
    ur: ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"],
    hi: ["जनवरी", "फ़रवरी", "मार्च", "अप्रैल", "मई", "जून", "जुलाई", "अगस्त", "सितंबर", "अक्तूबर", "नवंबर", "दिसंबर"],
    bn: ["জানুয়ারি", "ফেব্রুয়ারি", "মার্চ", "এপ্রিল", "মে", "জুন", "জুলাই", "আগস্ট", "সেপ্টেম্বর", "অক্টোবর", "নভেম্বর", "ডিসেম্বর"],
    ud: ["جنوری", "فروری", "مارچ", "اپریل", "مئی", "جون", "جولائی", "اگست", "ستمبر", "اکتوبر", "نومبر", "دسمبر"],
    zh: ["一月", "二月", "三月", "四月", "五月", "六月", "七月", "八月", "九月", "十月", "十一月", "十二月"],
    de: ["Januar", "Februar", "März", "April", "Mai", "Juni", "Juli", "August", "September", "Oktober", "November", "Dezember"],
    it: ["gennaio", "febbraio", "marzo", "aprile", "maggio", "giugno", "luglio", "agosto", "settembre", "ottobre", "novembre", "dicembre"],
    ru: ["январь", "февраль", "март", "апрель", "май", "июнь", "июль", "август", "сентябрь", "октябрь", "ноябрь", "декабрь"],
    tr: ["Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran", "Temmuz", "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık"],
    ko: ["1월", "2월", "3월", "4월", "5월", "6월", "7월", "8월", "9월", "10월", "11월", "12월"],
    ja: ["1月", "2月", "3月", "4月", "5月", "6月", "7月", "8月", "9月", "10月", "11月", "12月"],
    vi: ["tháng 1", "tháng 2", "tháng 3", "tháng 4", "tháng 5", "tháng 6", "tháng 7", "tháng 8", "tháng 9", "tháng 10", "tháng 11", "tháng 12"],
    fa: ["ژانویه", "فوریه", "مارس", "آوریل", "مه", "ژوئن", "ژوئیه", "اوت", "سپتامبر", "اکتبر", "نوامبر", "دسامبر"],
    th: ["มกราคม", "กุมภาพันธ์", "มีนาคม", "เมษายน", "พฤษภาคม", "มิถุนายน", "กรกฎาคม", "สิงหาคม", "กันยายน", "ตุลาคม", "พฤศจิกายน", "ธันวาคม"]
  },
  months_short: {
    en: ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"],
    es: ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sept", "oct", "nov", "dic"],
    fr: ["janv.", "févr.", "mars", "avr.", "mai", "juin", "juil.", "août", "sept.", "oct.", "nov.", "déc."],
    ar: ["يناير", "فبراير", "مارس", "أبريل", "مايو", "يونيو", "يوليو", "أغسطس", "سبتمبر", "أكتوبر", "نوفمبر", "ديسمبر"],
    pt: ["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"],
    ur: ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"],
    hi: ["जन", "फ़र", "मार्च", "अप्रैल", "मई", "जून", "जुला", "अग", "सितं", "अक्तू", "नवं", "दिसं"],
    bn: ["জানু", "ফেব্রু", "মার্চ", "এপ্রিল", "মে", "জুন", "জুলাই", "আগস্ট", "সেপ্টে", "অক্টো", "নভে", "ডিসে"],
    ud: ["جنوری", "فروری", "مارچ", "اپریل", "مئی", "جون", "جولائی", "اگست", "ستمبر", "اکتوبر", "نومبر", "دسمبر"],
    zh: ["1月", "2月", "3月", "4月", "5月", "6月", "7月", "8月", "9月", "10月", "11月", "12月"],
    de: ["Jan", "Feb", "Mär", "Apr", "Mai", "Jun", "Jul", "Aug", "Sep", "Okt", "Nov", "Dez"],
    it: ["gen", "feb", "mar", "apr", "mag", "giu", "lug", "ago", "set", "ott", "nov", "dic"],
    ru: ["янв", "фев", "мар", "апр", "май", "июн", "июл", "авг", "сен", "окт", "ноя", "дек"],
    tr: ["Oca", "Şub", "Mar", "Nis", "May", "Haz", "Tem", "Ağu", "Eyl", "Eki", "Kas", "Ara"],
    ko: ["1월", "2월", "3월", "4월", "5월", "6월", "7월", "8월", "9월", "10월", "11월", "12월"],
    ja: ["1月", "2月", "3月", "4月", "5月", "6月", "7月", "8月", "9月", "10月", "11月", "12月"],
    vi: ["Th1", "Th2", "Th3", "Th4", "Th5", "Th6", "Th7", "Th8", "Th9", "Th10", "Th11", "Th12"],
    fa: ["ژان", "فوریه", "مارس", "آور", "مه", "ژوئن", "ژوئیه", "اوت", "سپت", "اکت", "نوا", "دسا"],
    th: ["ม.ค.", "ก.พ.", "มี.ค.", "เม.ย.", "พ.ค.", "มิ.ย.", "ก.ค.", "ส.ค.", "ก.ย.", "ต.ค.", "พ.ย.", "ธ.ค."]
  },
  days_short: {
    en: ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"],
    es: ["dom", "lun", "mar", "mié", "jue", "vie", "sáb"],
    fr: ["dim.", "lun.", "mar.", "mer.", "jeu.", "ven.", "sam."],
    ar: ["الأحد", "الاثنين", "الثلاثاء", "الأربعاء", "الخميس", "الجمعة", "السبت"],
    pt: ["dom", "seg", "ter", "qua", "qui", "sex", "sáb"],
    ur: ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"],
    hi: ["रवि", "सोम", "मंगल", "बुध", "गुरु", "शुक्र", "शनि"],
    bn: ["রবি", "সোম", "মঙ্গল", "বুধ", "বৃহস্পতি", "শুক্র", "শনি"],
    ud: ["اتوار", "پیر", "منگل", "بدھ", "جمعرات", "جمعہ", "ہفتہ"],
    zh: ["周日", "周一", "周二", "周三", "周四", "周五", "周六"],
    de: ["So", "Mo", "Di", "Mi", "Do", "Fr", "Sa"],
    it: ["dom", "lun", "mar", "mer", "gio", "ven", "sab"],
    ru: ["вс", "пн", "вт", "ср", "чт", "пт", "сб"],
    tr: ["Paz", "Pzt", "Sal", "Çar", "Per", "Cum", "Cmt"],
    ko: ["일", "월", "화", "수", "목", "금", "토"],
    ja: ["日", "月", "火", "水", "木", "金", "土"],
    vi: ["CN", "T2", "T3", "T4", "T5", "T6", "T7"],
    fa: ["یک", "دو", "سه", "چهار", "پنج", "جمع", "شنبه"],
    th: ["อา.", "จ.", "อ.", "พ.", "พฤ.", "ศ.", "ส."]
  }
};
