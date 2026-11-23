/* Noel Chauffer — site translations + language switcher runtime.
   Languages: en (English US), es (Spanish), fr (French), ar (Arabic),
   pt (Portuguese), ur (Roman Urdu), hi (Hindi), bn (Bengali).
   Class names (Business Class / Business SUV / First Class) stay English
   in every language — they are product names. Money, dates, addresses
   and airport codes are never translated. Arabic is right-to-left.
   The choice persists in localStorage under "noel-language" and is
   shared by the website and the customer app (/app). */
var NOEL_I18N = {};

NOEL_I18N["menu.our_services"] = {
  "en": "Our services", "es": "Nuestros servicios", "fr": "Nos services",
  "ar": "خدماتنا", "pt": "Nossos serviços",
  "ur": "Hamari services", "hi": "हमारी सेवाएँ", "bn": "আমাদের পরিষেবা"
};
NOEL_I18N["menu.city_to_city"] = {
  "en": "City-to-City rides", "es": "Viajes de ciudad a ciudad", "fr": "Trajets de ville à ville",
  "ar": "رحلات من مدينة إلى مدينة", "pt": "Viagens de cidade a cidade",
  "ur": "City-to-City rides", "hi": "शहर से शहर की सवारी", "bn": "শহর থেকে শহরে রাইড"
};
NOEL_I18N["menu.chauffeur_hailing"] = {
  "en": "Chauffeur hailing", "es": "Chófer a pedido", "fr": "Chauffeur à la demande",
  "ar": "استدعاء سائق", "pt": "Motorista sob demanda",
  "ur": "Chauffeur hailing", "hi": "शॉफ़र हेलिंग", "bn": "শোফার হেইলিং"
};
NOEL_I18N["menu.airport_transfers"] = {
  "en": "Airport transfers", "es": "Traslados al aeropuerto", "fr": "Transferts aéroport",
  "ar": "النقل من وإلى المطار", "pt": "Transfers de aeroporto",
  "ur": "Airport transfers", "hi": "एयरपोर्ट ट्रांसफर", "bn": "বিমানবন্দর ট্রান্সফার"
};
NOEL_I18N["menu.hourly_hire"] = {
  "en": "Hourly hire", "es": "Alquiler por horas", "fr": "Location à l'heure",
  "ar": "الحجز بالساعة", "pt": "Aluguel por hora",
  "ur": "Hourly hire", "hi": "घंटे के हिसाब से किराया", "bn": "ঘণ্টা হিসেবে ভাড়া"
};
NOEL_I18N["menu.chauffeur_service"] = {
  "en": "Chauffeur service", "es": "Servicio de chófer", "fr": "Service de chauffeur",
  "ar": "خدمة السائق", "pt": "Serviço de motorista",
  "ur": "Chauffeur service", "hi": "शॉफ़र सेवा", "bn": "শোফার পরিষেবা"
};
NOEL_I18N["menu.limousine"] = {
  "en": "Limousine service", "es": "Servicio de limusina", "fr": "Service de limousine",
  "ar": "خدمة الليموزين", "pt": "Serviço de limusine",
  "ur": "Limousine service", "hi": "लिमोज़िन सेवा", "bn": "লিমুজিন পরিষেবা"
};
NOEL_I18N["menu.for_business"] = {
  "en": "For business", "es": "Para empresas", "fr": "Pour les entreprises",
  "ar": "للأعمال", "pt": "Para empresas",
  "ur": "Business ke liye", "hi": "व्यवसाय के लिए", "bn": "ব্যবসার জন্য"
};
NOEL_I18N["menu.overview"] = {
  "en": "Overview", "es": "Resumen", "fr": "Aperçu",
  "ar": "نظرة عامة", "pt": "Visão geral",
  "ur": "Overview", "hi": "अवलोकन", "bn": "সংক্ষিপ্ত বিবরণ"
};
NOEL_I18N["menu.corporations"] = {
  "en": "Corporations", "es": "Empresas", "fr": "Entreprises",
  "ar": "الشركات", "pt": "Empresas",
  "ur": "Corporations", "hi": "कॉर्पोरेशन", "bn": "কর্পোরেশন"
};
NOEL_I18N["menu.travel_agencies"] = {
  "en": "Travel agencies", "es": "Agencias de viajes", "fr": "Agences de voyages",
  "ar": "وكالات السفر", "pt": "Agências de viagens",
  "ur": "Travel agencies", "hi": "ट्रैवल एजेंसियाँ", "bn": "ট্রাভেল এজেন্সি"
};
NOEL_I18N["menu.partnerships"] = {
  "en": "Strategic partnerships", "es": "Alianzas estratégicas", "fr": "Partenariats stratégiques",
  "ar": "شراكات استراتيجية", "pt": "Parcerias estratégicas",
  "ur": "Strategic partnerships", "hi": "रणनीतिक साझेदारियाँ", "bn": "কৌশলগত অংশীদারিত্ব"
};
NOEL_I18N["menu.your_rides"] = {
  "en": "Your rides", "es": "Tus viajes", "fr": "Vos trajets",
  "ar": "رحلاتك", "pt": "Suas viagens",
  "ur": "Aapki rides", "hi": "आपकी सवारियाँ", "bn": "আপনার রাইডগুলো"
};
NOEL_I18N["menu.help"] = {
  "en": "Help", "es": "Ayuda", "fr": "Aide",
  "ar": "مساعدة", "pt": "Ajuda",
  "ur": "Help", "hi": "सहायता", "bn": "সহায়তা"
};
NOEL_I18N["menu.sign_in"] = {
  "en": "Sign in", "es": "Iniciar sesión", "fr": "Se connecter",
  "ar": "تسجيل الدخول", "pt": "Entrar",
  "ur": "Sign in", "hi": "साइन इन करें", "bn": "সাইন ইন করুন"
};
NOEL_I18N["menu.sign_out"] = {
  "en": "Sign out", "es": "Cerrar sesión", "fr": "Se déconnecter",
  "ar": "تسجيل الخروج", "pt": "Sair",
  "ur": "Sign out", "hi": "साइन आउट करें", "bn": "সাইন আউট করুন"
};
NOEL_I18N["menu.signin_fill"] = {
  "en": "Please enter your email and phone number.",
  "es": "Introduce tu correo electrónico y tu número de teléfono.",
  "fr": "Veuillez saisir votre e-mail et votre numéro de téléphone.",
  "ar": "يرجى إدخال بريدك الإلكتروني ورقم هاتفك.",
  "pt": "Informe seu e-mail e número de telefone.",
  "ur": "Apna email aur phone number likhen.",
  "hi": "कृपया अपना ईमेल और फ़ोन नंबर दर्ज करें।",
  "bn": "আপনার ইমেইল এবং ফোন নম্বর লিখুন।"
};
NOEL_I18N["menu.open"] = {
  "en": "Open menu", "es": "Abrir menú", "fr": "Ouvrir le menu",
  "ar": "افتح القائمة", "pt": "Abrir menu",
  "ur": "Menu kholen", "hi": "मेनू खोलें", "bn": "মেনু খুলুন"
};
NOEL_I18N["menu.close"] = {
  "en": "Close menu", "es": "Cerrar menú", "fr": "Fermer le menu",
  "ar": "أغلق القائمة", "pt": "Fechar menu",
  "ur": "Menu band karen", "hi": "मेनू बंद करें", "bn": "মেনু বন্ধ করুন"
};
NOEL_I18N["menu.your_ride"] = {
  "en": "Your ride", "es": "Tu viaje", "fr": "Votre trajet",
  "ar": "رحلتك", "pt": "Sua viagem",
  "ur": "Aapki ride", "hi": "आपकी सवारी", "bn": "আপনার রাইড"
};
NOEL_I18N["menu.why_us"] = {
  "en": "Why us", "es": "Por qué nosotros", "fr": "Pourquoi nous",
  "ar": "لماذا نحن", "pt": "Por que nós",
  "ur": "Hum kyun", "hi": "हम क्यों", "bn": "আমরা কেন"
};
NOEL_I18N["menu.cancellation"] = {
  "en": "Cancellation & waiting", "es": "Cancelación y espera", "fr": "Annulation et attente",
  "ar": "الإلغاء والانتظار", "pt": "Cancelamento e espera",
  "ur": "Cancellation & waiting", "hi": "रद्दीकरण और प्रतीक्षा", "bn": "বাতিল ও অপেক্ষা"
};
NOEL_I18N["menu.faq"] = {
  "en": "FAQ", "es": "Preguntas frecuentes", "fr": "FAQ",
  "ar": "الأسئلة الشائعة", "pt": "Perguntas frequentes",
  "ur": "FAQ", "hi": "सामान्य प्रश्न", "bn": "সাধারণ প্রশ্ন"
};
NOEL_I18N["menu.our_company"] = {
  "en": "Our company", "es": "Nuestra empresa", "fr": "Notre entreprise",
  "ar": "شركتنا", "pt": "Nossa empresa",
  "ur": "Hamari company", "hi": "हमारी कंपनी", "bn": "আমাদের কোম্পানি"
};
NOEL_I18N["menu.contacts"] = {
  "en": "Contacts", "es": "Contactos", "fr": "Contacts",
  "ar": "اتصل بنا", "pt": "Contatos",
  "ur": "Contacts", "hi": "संपर्क", "bn": "যোগাযোগ"
};
NOEL_I18N["menu.ride_history"] = {
  "en": "Ride history", "es": "Historial de viajes", "fr": "Historique des trajets",
  "ar": "سجل الرحلات", "pt": "Histórico de viagens",
  "ur": "Ride history", "hi": "सवारी इतिहास", "bn": "রাইডের ইতিহাস"
};
NOEL_I18N["menu.experience"] = {
  "en": "Experience", "es": "Experiencia", "fr": "Expérience",
  "ar": "التجربة", "pt": "Experiência",
  "ur": "Experience", "hi": "अनुभव", "bn": "অভিজ্ঞতা"
};

/* ---- Booking form (website + app share these keys) ---- */
NOEL_I18N["form.your_ride"] = {
  "en": "Your ride", "es": "Tu viaje", "fr": "Votre trajet",
  "ar": "رحلتك", "pt": "Sua viagem",
  "ur": "Aapki ride", "hi": "आपकी सवारी", "bn": "আপনার রাইড"
};
NOEL_I18N["form.one_way"] = {
  "en": "One way", "es": "Solo ida", "fr": "Aller simple",
  "ar": "اتجاه واحد", "pt": "Somente ida",
  "ur": "One way", "hi": "एक तरफा", "bn": "এক দিকে"
};
NOEL_I18N["form.by_the_hour"] = {
  "en": "By the hour", "es": "Por horas", "fr": "À l'heure",
  "ar": "بالساعة", "pt": "Por hora",
  "ur": "By the hour", "hi": "घंटे के हिसाब से", "bn": "ঘণ্টা হিসেবে"
};
NOEL_I18N["form.select_date"] = {
  "en": "Select a date", "es": "Selecciona una fecha", "fr": "Sélectionnez une date",
  "ar": "اختر تاريخًا", "pt": "Selecione uma data",
  "ur": "Date chunen", "hi": "तारीख़ चुनें", "bn": "তারিখ বেছে নিন"
};
NOEL_I18N["form.select_time"] = {
  "en": "Select a time", "es": "Selecciona una hora", "fr": "Sélectionnez une heure",
  "ar": "اختر وقتًا", "pt": "Selecione um horário",
  "ur": "Time chunen", "hi": "समय चुनें", "bn": "সময় বেছে নিন"
};
NOEL_I18N["form.choose_date"] = {
  "en": "Choose a date", "es": "Elige una fecha", "fr": "Choisissez une date",
  "ar": "اختر تاريخًا", "pt": "Escolha uma data",
  "ur": "Date chunen", "hi": "तारीख़ चुनें", "bn": "তারিখ বেছে নিন"
};
NOEL_I18N["form.phone_ph"] = {
  "en": "Your phone number", "es": "Tu número de teléfono", "fr": "Votre numéro de téléphone",
  "ar": "رقم هاتفك", "pt": "Seu número de telefone",
  "ur": "Aapka phone number", "hi": "आपका फ़ोन नंबर", "bn": "আপনার ফোন নম্বর"
};
NOEL_I18N["form.flight_ph_short"] = {
  "en": "e.g. EK215", "es": "p. ej., EK215", "fr": "p. ex. EK215",
  "ar": "مثال: EK215", "pt": "ex.: EK215",
  "ur": "e.g. EK215", "hi": "जैसे EK215", "bn": "যেমন EK215"
};
NOEL_I18N["form.back_to_form"] = {
  "en": "← Back to booking form", "es": "← Volver al formulario de reserva", "fr": "← Retour au formulaire de réservation",
  "ar": "← العودة إلى نموذج الحجز", "pt": "← Voltar ao formulário de reserva",
  "ur": "← Booking form par wapas", "hi": "← बुकिंग फ़ॉर्म पर वापस जाएँ", "bn": "← বুকিং ফর্মে ফিরে যান"
};
NOEL_I18N["form.pay"] = {
  "en": "Pay", "es": "Pagar", "fr": "Payer",
  "ar": "ادفع", "pt": "Pagar",
  "ur": "Pay karen", "hi": "भुगतान करें", "bn": "পেমেন্ট করুন"
};
NOEL_I18N["hourly.miles_note"] = {
  "en": "Includes {total} miles of travel ({per_hour} miles per hour) — taxes and tolls included.",
  "es": "Incluye {total} millas de viaje ({per_hour} millas por hora); impuestos y peajes incluidos.",
  "fr": "Comprend {total} miles de trajet ({per_hour} miles par heure) — taxes et péages inclus.",
  "ar": "يشمل {total} ميلًا من السفر ({per_hour} ميلًا في الساعة) — الضرائب والرسوم مشمولة.",
  "pt": "Inclui {total} milhas de viagem ({per_hour} milhas por hora) — impostos e pedágios incluídos.",
  "ur": "{total} miles travel shamil hai ({per_hour} miles per hour) — taxes aur tolls shamil hain.",
  "hi": "{total} मील की यात्रा शामिल है (प्रति घंटे {per_hour} मील) — कर और टोल शामिल हैं।",
  "bn": "{total} মাইল ভ্রমণ অন্তর্ভুক্ত (প্রতি ঘণ্টায় {per_hour} মাইল) — কর ও টোল অন্তর্ভুক্ত।"
};
NOEL_I18N["status.booking_cancelled_heading"] = {
  "en": "Booking cancelled", "es": "Reserva cancelada", "fr": "Réservation annulée",
  "ar": "تم إلغاء الحجز", "pt": "Reserva cancelada",
  "ur": "Booking cancel ho gayi", "hi": "बुकिंग रद्द कर दी गई", "bn": "বুকিং বাতিল করা হয়েছে"
};
NOEL_I18N["status.flight_label"] = {
  "en": "Flight", "es": "Vuelo", "fr": "Vol",
  "ar": "الرحلة", "pt": "Voo",
  "ur": "Flight", "hi": "फ़्लाइट", "bn": "ফ্লাইট"
};
NOEL_I18N["form.pickup"] = {
  "en": "Pickup address", "es": "Dirección de recogida", "fr": "Adresse de prise en charge",
  "ar": "عنوان الاستلام", "pt": "Endereço de embarque",
  "ur": "Pickup address", "hi": "पिकअप का पता", "bn": "পিকআপের ঠিকানা"
};
NOEL_I18N["form.pickup_ph"] = {
  "en": "Where from?", "es": "¿Desde dónde?", "fr": "D'où partez-vous ?",
  "ar": "من أين؟", "pt": "De onde?",
  "ur": "Kahan se?", "hi": "कहाँ से?", "bn": "কোথা থেকে?"
};
NOEL_I18N["form.dropoff"] = {
  "en": "Drop-off address", "es": "Dirección de destino", "fr": "Adresse de destination",
  "ar": "عنوان الوصول", "pt": "Endereço de destino",
  "ur": "Drop-off address", "hi": "ड्रॉप-ऑफ़ का पता", "bn": "ড্রপ-অফের ঠিকানা"
};
NOEL_I18N["form.dropoff_ph"] = {
  "en": "Where to?", "es": "¿Adónde?", "fr": "Où allez-vous ?",
  "ar": "إلى أين؟", "pt": "Para onde?",
  "ur": "Kahan tak?", "hi": "कहाँ तक?", "bn": "কোথায় যাবেন?"
};
NOEL_I18N["form.date"] = {
  "en": "Date", "es": "Fecha", "fr": "Date",
  "ar": "التاريخ", "pt": "Data",
  "ur": "Date", "hi": "तारीख", "bn": "তারিখ"
};
NOEL_I18N["form.pickup_time"] = {
  "en": "Pickup time", "es": "Hora de recogida", "fr": "Heure de prise en charge",
  "ar": "وقت الاستلام", "pt": "Hora de embarque",
  "ur": "Pickup time", "hi": "पिकअप का समय", "bn": "পিকআপের সময়"
};
NOEL_I18N["form.flight_number"] = {
  "en": "Flight number", "es": "Número de vuelo", "fr": "Numéro de vol",
  "ar": "رقم الرحلة", "pt": "Número do voo",
  "ur": "Flight number", "hi": "फ़्लाइट नंबर", "bn": "ফ্লাইট নম্বর"
};
NOEL_I18N["form.flight_ph"] = {
  "en": "e.g. LH202, BA2490", "es": "p. ej., LH202, BA2490", "fr": "p. ex. LH202, BA2490",
  "ar": "مثال: LH202, BA2490", "pt": "ex.: LH202, BA2490",
  "ur": "e.g. LH202, BA2490", "hi": "जैसे LH202, BA2490", "bn": "যেমন LH202, BA2490"
};
NOEL_I18N["form.hours"] = {
  "en": "Hours", "es": "Horas", "fr": "Heures",
  "ar": "الساعات", "pt": "Horas",
  "ur": "Hours", "hi": "घंटे", "bn": "ঘণ্টা"
};
NOEL_I18N["form.hours_hint"] = {
  "en": "Minimum 2 hours, maximum 24. Your chauffeur stays with you for the hours you book.",
  "es": "Mínimo 2 horas, máximo 24. Tu chófer se queda contigo durante las horas reservadas.",
  "fr": "Minimum 2 heures, maximum 24. Votre chauffeur reste avec vous pendant les heures réservées.",
  "ar": "الحد الأدنى ساعتان، والحد الأقصى 24 ساعة. يبقى سائقك معك طوال الساعات التي تحجزها.",
  "pt": "Mínimo de 2 horas, máximo de 24. Seu motorista fica com você durante as horas reservadas.",
  "ur": "Kam se kam 2 hours, zyada se zyada 24. Aapka chauffeur utni der aapke saath rahega jitne hours aap book karenge.",
  "hi": "कम से कम 2 घंटे, अधिकतम 24। आपका शॉफ़र उतने समय तक आपके साथ रहेगा जितने घंटे आप बुक करेंगे।",
  "bn": "সর্বনিম্ন ২ ঘণ্টা, সর্বোচ্চ ২৪। আপনার শোফার যত ঘণ্টা বুক করবেন ততক্ষণ আপনার সঙ্গে থাকবেন।"
};
NOEL_I18N["form.view_options"] = {
  "en": "View options", "es": "Ver opciones", "fr": "Voir les options",
  "ar": "عرض الخيارات", "pt": "Ver opções",
  "ur": "Options dekhen", "hi": "विकल्प देखें", "bn": "বিকল্প দেখুন"
};
NOEL_I18N["form.required"] = {
  "en": "This field is required", "es": "Este campo es obligatorio", "fr": "Ce champ est obligatoire",
  "ar": "هذا الحقل مطلوب", "pt": "Este campo é obrigatório",
  "ur": "Ye field zaroori hai", "hi": "यह फ़ील्ड ज़रूरी है", "bn": "এই ঘরটি পূরণ করা আবশ্যক"
};
NOEL_I18N["form.sending"] = {
  "en": "Sending your request…", "es": "Enviando tu solicitud…", "fr": "Envoi de votre demande…",
  "ar": "جارٍ إرسال طلبك…", "pt": "Enviando sua solicitação…",
  "ur": "Aapki request bheji ja rahi hai…", "hi": "आपका अनुरोध भेजा जा रहा है…", "bn": "আপনার অনুরোধ পাঠানো হচ্ছে…"
};
NOEL_I18N["form.paused"] = {
  "en": "Bookings are paused while we update our prices. Please check back soon.",
  "es": "Las reservas están en pausa mientras actualizamos nuestros precios. Vuelve pronto.",
  "fr": "Les réservations sont suspendues pendant la mise à jour de nos tarifs. Revenez bientôt.",
  "ar": "الحجوزات متوقفة مؤقتًا أثناء تحديث أسعارنا. يرجى العودة قريبًا.",
  "pt": "As reservas estão pausadas enquanto atualizamos nossos preços. Volte em breve.",
  "ur": "Prices update ho rahe hain is liye bookings ruki hui hain. Thodi der mein phir check karen.",
  "hi": "हमारे दाम अपडेट हो रहे हैं, इसलिए बुकिंग रुकी हुई है। कृपया थोड़ी देर में फिर देखें।",
  "bn": "আমাদের দাম আপডেট হচ্ছে বলে বুকিং সাময়িক বন্ধ আছে। শীঘ্রই আবার দেখুন।"
};
NOEL_I18N["form.hourly_need"] = {
  "en": "Hourly bookings need 2 to 24 hours.", "es": "Las reservas por horas necesitan de 2 a 24 horas.",
  "fr": "Les réservations à l'heure nécessitent de 2 à 24 heures.",
  "ar": "الحجز بالساعة يحتاج من ساعتين إلى 24 ساعة.",
  "pt": "Reservas por hora precisam de 2 a 24 horas.",
  "ur": "Hourly booking ke liye 2 se 24 hours chahiye.",
  "hi": "घंटे वाली बुकिंग के लिए 2 से 24 घंटे चाहिए।",
  "bn": "ঘণ্টা হিসেবে বুকিংয়ের জন্য ২ থেকে ২৪ ঘণ্টা লাগবে।"
};
NOEL_I18N["form.choose_datetime"] = {
  "en": "Please choose a date and time.", "es": "Elige una fecha y una hora.",
  "fr": "Veuillez choisir une date et une heure.",
  "ar": "يرجى اختيار التاريخ والوقت.",
  "pt": "Escolha uma data e uma hora.",
  "ur": "Date aur time chunen.",
  "hi": "कृपया तारीख और समय चुनें।",
  "bn": "দয়া করে তারিখ ও সময় বেছে নিন।"
};
NOEL_I18N["form.past_date"] = {
  "en": "Please choose a date from today onwards. Past dates cannot be booked.",
  "es": "Elige una fecha a partir de hoy. No se pueden reservar fechas pasadas.",
  "fr": "Veuillez choisir une date à partir d'aujourd'hui. Les dates passées ne peuvent pas être réservées.",
  "ar": "يرجى اختيار تاريخ من اليوم فصاعدًا. لا يمكن حجز التواريخ الماضية.",
  "pt": "Escolha uma data a partir de hoje. Datas passadas não podem ser reservadas.",
  "ur": "Aaj se aage ki date chunen. Beeti hui date book nahi ho sakti.",
  "hi": "कृपया आज से आगे की तारीख चुनें। बीती तारीख बुक नहीं हो सकती।",
  "bn": "দয়া করে আজ থেকে পরের কোনো তারিখ বেছে নিন। আগের তারিখ বুক করা যাবে না।"
};
NOEL_I18N["form.past_time"] = {
  "en": "Please choose a time later than now. Past times cannot be booked.",
  "es": "Elige una hora posterior a la actual. No se pueden reservar horas pasadas.",
  "fr": "Veuillez choisir une heure ultérieure. Les heures passées ne peuvent pas être réservées.",
  "ar": "يرجى اختيار وقت لاحق للوقت الحالي. لا يمكن حجز الأوقات الماضية.",
  "pt": "Escolha um horário posterior ao atual. Horários passados não podem ser reservados.",
  "ur": "Ab se baad ka time chunen. Beeta hua time book nahi ho sakta.",
  "hi": "कृपया अभी से बाद का समय चुनें। बीता समय बुक नहीं हो सकता।",
  "bn": "দয়া করে এখনকার চেয়ে পরের সময় বেছে নিন। আগের সময় বুক করা যাবে না।"
};
NOEL_I18N["form.fill_details"] = {
  "en": "Please fill in your name, phone and email.",
  "es": "Completa tu nombre, teléfono y correo electrónico.",
  "fr": "Veuillez renseigner votre nom, votre téléphone et votre e-mail.",
  "ar": "يرجى إدخال اسمك ورقم هاتفك وبريدك الإلكتروني.",
  "pt": "Preencha seu nome, telefone e e-mail.",
  "ur": "Apna naam, phone aur email likhen.",
  "hi": "कृपया अपना नाम, फ़ोन और ईमेल भरें।",
  "bn": "দয়া করে আপনার নাম, ফোন ও ইমেইল লিখুন।"
};
NOEL_I18N["form.continue"] = {
  "en": "Continue", "es": "Continuar", "fr": "Continuer",
  "ar": "متابعة", "pt": "Continuar",
  "ur": "Continue", "hi": "जारी रखें", "bn": "চালিয়ে যান"
};
NOEL_I18N["form.skip"] = {
  "en": "Skip", "es": "Omitir", "fr": "Passer",
  "ar": "تخطَّ", "pt": "Pular",
  "ur": "Skip karen", "hi": "छोड़ें", "bn": "এড়িয়ে যান"
};
NOEL_I18N["form.flight_title"] = {
  "en": "Add your flight number", "es": "Añade tu número de vuelo",
  "fr": "Ajoutez votre numéro de vol",
  "ar": "أضف رقم رحلتك", "pt": "Adicione o número do seu voo",
  "ur": "Apni flight number likhen", "hi": "अपनी फ़्लाइट संख्या जोड़ें", "bn": "আপনার ফ্লাইট নম্বর যোগ করুন"
};
NOEL_I18N["form.flight_title_opt"] = {
  "en": "Add your flight number (optional)", "es": "Añade tu número de vuelo (opcional)",
  "fr": "Ajoutez votre numéro de vol (facultatif)",
  "ar": "أضف رقم رحلتك (اختياري)", "pt": "Adicione o número do seu voo (opcional)",
  "ur": "Apni flight number likhen (optional)", "hi": "अपनी फ़्लाइट संख्या जोड़ें (वैकल्पिक)", "bn": "আপনার ফ্লাইট নম্বর যোগ করুন (ঐচ্ছিক)"
};
NOEL_I18N["form.flight_text_pickup"] = {
  "en": "Your chauffeur will meet you at the right terminal.",
  "es": "Tu chófer te esperará en la terminal correcta.",
  "fr": "Votre chauffeur vous attendra au bon terminal.",
  "ar": "سيقابلك سائقك في الصالة الصحيحة.",
  "pt": "Seu motorista encontrará você no terminal certo.",
  "ur": "Aapka chauffeur sahi terminal par aapko milega.",
  "hi": "आपका शॉफ़र सही टर्मिनल पर आपसे मिलेगा।",
  "bn": "আপনার শোফার সঠিক টার্মিনালে আপনার সঙ্গে দেখা করবেন।"
};
NOEL_I18N["form.flight_text_dropoff"] = {
  "en": "This helps your chauffeur take you to the right departure terminal.",
  "es": "Esto ayuda a tu chófer a llevarte a la terminal de salida correcta.",
  "fr": "Cela aide votre chauffeur à vous conduire au bon terminal de départ.",
  "ar": "يساعد هذا سائقك على إيصالك إلى صالة المغادرة الصحيحة.",
  "pt": "Isso ajuda seu motorista a levá-lo ao terminal de embarque certo.",
  "ur": "Is se aapka chauffeur aapko sahi departure terminal tak le jayega.",
  "hi": "इससे आपका शॉफ़र आपको सही प्रस्थान टर्मिनल तक ले जाएगा।",
  "bn": "এতে আপনার শোফার আপনাকে সঠিক যাত্রা টার্মিনালে নিয়ে যেতে পারবেন।"
};
NOEL_I18N["form.flight_skip_note"] = {
  "en": "You can skip this — your booking will still go through.",
  "es": "Puedes omitir esto: tu reserva seguirá adelante.",
  "fr": "Vous pouvez passer cette étape — votre réservation sera quand même confirmée.",
  "ar": "يمكنك تخطي هذه الخطوة — وسيتم حجزك على أي حال.",
  "pt": "Você pode pular esta etapa — sua reserva seguirá normalmente.",
  "ur": "Aap ye skip kar sakte hain — aapki booking phir bhi ho jayegi.",
  "hi": "आप इसे छोड़ सकते हैं — आपकी बुकिंग फिर भी हो जाएगी।",
  "bn": "আপনি এটা এড়িয়ে যেতে পারেন — আপনার বুকিং তবুও হয়ে যাবে।"
};

/* ---- Class page ("Choose your experience") ---- */
NOEL_I18N["class.ny_congestion"] = {
  "en": "NY State congestion surcharge", "es": "Recargo por congestión del estado de Nueva York",
  "fr": "Supplément de congestion de l'État de New York",
  "ar": "رسوم ازدحام ولاية نيويورك", "pt": "Sobretaxa de congestionamento do estado de Nova York",
  "ur": "NY State congestion surcharge", "hi": "न्यूयॉर्क राज्य भीड़ अधिभार", "bn": "নিউ ইয়র্ক স্টেট যানজট সারচার্জ"
};
NOEL_I18N["class.mta_congestion"] = {
  "en": "MTA congestion surcharge", "es": "Recargo por congestión de la MTA",
  "fr": "Supplément de congestion MTA",
  "ar": "رسوم ازدحام MTA", "pt": "Sobretaxa de congestionamento da MTA",
  "ur": "MTA congestion surcharge", "hi": "MTA भीड़ अधिभार", "bn": "MTA যানজট সারচার্জ"
};
NOEL_I18N["class.referral_discount"] = {
  "en": "Referral discount", "es": "Descuento por recomendación", "fr": "Remise de parrainage",
  "ar": "خصم الإحالة", "pt": "Desconto por indicação",
  "ur": "Referral discount", "hi": "रेफ़रल छूट", "bn": "রেফারেল ছাড়"
};
NOEL_I18N["class.discount_note"] = {
  "en": "Referral discount applied — 5% off your first ride.",
  "es": "Descuento por recomendación aplicado: 5 % de descuento en tu primer viaje.",
  "fr": "Remise de parrainage appliquée — 5 % de réduction sur votre premier trajet.",
  "ar": "تم تطبيق خصم الإحالة — خصم 5٪ على رحلتك الأولى.",
  "pt": "Desconto por indicação aplicado — 5% de desconto na sua primeira viagem.",
  "ur": "Referral discount lag gaya — pehli ride par 5% off.",
  "hi": "रेफ़रल छूट लागू — आपकी पहली सवारी पर 5% की छूट।",
  "bn": "রেফারেল ছাড় প্রযোজ্য — আপনার প্রথম রাইডে ৫% ছাড়।"
};
NOEL_I18N["class.hl_comfort"] = {
  "en": "Clean, quiet, and executive-level comfort.",
  "es": "Comodidad limpia, silenciosa y de nivel ejecutivo.",
  "fr": "Un confort propre, silencieux et de niveau exécutif.",
  "ar": "راحة نظيفة وهادئة وبمستوى تنفيذي.",
  "pt": "Conforto limpo, silencioso e de nível executivo.",
  "ur": "Saaf, khamosh aur executive-level comfort.",
  "hi": "स्वच्छ, शांत और कार्यकारी स्तर का आराम।",
  "bn": "পরিষ্কার, শান্ত ও এক্সিকিউটিভ-স্তরের আরাম।"
};
NOEL_I18N["class.hl_charged"] = {
  "en": "Arrive fully charged", "es": "Llega con la batería llena", "fr": "Arrivez complètement chargé",
  "ar": "صِل وبطاريتك مشحونة بالكامل", "pt": "Chegue com a bateria cheia",
  "ur": "Full charge ke saath pahunchen", "hi": "पूरी तरह चार्ज होकर पहुँचें", "bn": "সম্পূর্ণ চার্জ নিয়ে পৌঁছান"
};
NOEL_I18N["class.hl_charged_text"] = {
  "en": "Phone chargers in every car, so your phone is full when you arrive.",
  "es": "Cargadores de teléfono en cada coche, para que tu teléfono esté lleno al llegar.",
  "fr": "Des chargeurs de téléphone dans chaque voiture, pour que votre téléphone soit chargé à votre arrivée.",
  "ar": "شواحن هواتف في كل سيارة، ليكون هاتفك مشحونًا بالكامل عند وصولك.",
  "pt": "Carregadores de celular em cada carro, para que seu telefone esteja carregado ao chegar.",
  "ur": "Har gaadi mein phone chargers, taaki aapka phone pahunchte waqt full ho.",
  "hi": "हर गाड़ी में फ़ोन चार्जर, ताकि पहुँचने पर आपका फ़ोन पूरा चार्ज हो।",
  "bn": "প্রতিটি গাড়িতে ফোন চার্জার, যাতে পৌঁছানোর সময় আপনার ফোন সম্পূর্ণ চার্জ থাকে।"
};
NOEL_I18N["class.cap_luggage_intro"] = {
  "en": "Based on standard luggage sizes, which may differ from yours.",
  "es": "Según los tamaños estándar de equipaje, que pueden diferir de los tuyos.",
  "fr": "Basé sur les tailles standard de bagages, qui peuvent différer des vôtres.",
  "ar": "بناءً على أحجام الأمتعة القياسية، التي قد تختلف عن أحجامك.",
  "pt": "Com base nos tamanhos padrão de bagagem, que podem diferir dos seus.",
  "ur": "Standard luggage sizes ke hisaab se, jo aapke se mukhtalif ho sakte hain.",
  "hi": "मानक सामान के आकार के आधार पर, जो आपके सामान से भिन्न हो सकता है।",
  "bn": "স্ট্যান্ডার্ড লাগেজের আকারের ভিত্তিতে, যা আপনার থেকে আলাদা হতে পারে।"
};
NOEL_I18N["class.cap_seating_suffix"] = {
  "en": "— please respect the seating capacity for safety.",
  "es": "— respeta la capacidad de asientos por seguridad.",
  "fr": "— veuillez respecter la capacité d'accueil pour votre sécurité.",
  "ar": "— يرجى احترام سعة المقاعد من أجل السلامة.",
  "pt": "— respeite a capacidade de assentos por segurança.",
  "ur": "— safety ke liye seating capacity ka khayal rakhen.",
  "hi": "— सुरक्षा के लिए कृपया बैठने की क्षमता का सम्मान करें।",
  "bn": "— নিরাপত্তার জন্য আসনের ধারণক্ষমতা মেনে চলুন।"
};
NOEL_I18N["status.pay_unreachable"] = {
  "en": "Could not reach the payment service. Please try again.",
  "es": "No se pudo contactar con el servicio de pago. Inténtalo de nuevo.",
  "fr": "Impossible de joindre le service de paiement. Veuillez réessayer.",
  "ar": "تعذّر الوصول إلى خدمة الدفع. يرجى المحاولة مرة أخرى.",
  "pt": "Não foi possível acessar o serviço de pagamento. Tente novamente.",
  "ur": "Payment service se rabta nahi ho saka. Dobara try karen.",
  "hi": "भुगतान सेवा से संपर्क नहीं हो सका। कृपया फिर से प्रयास करें।",
  "bn": "পেমেন্ট পরিষেবার সঙ্গে যোগাযোগ করা যায়নি। আবার চেষ্টা করুন।"
};
NOEL_I18N["status.fill_card_fields"] = {
  "en": "Please fill in all card fields.", "es": "Completa todos los campos de la tarjeta.",
  "fr": "Veuillez remplir tous les champs de la carte.",
  "ar": "يرجى ملء جميع حقول البطاقة.", "pt": "Preencha todos os campos do cartão.",
  "ur": "Card ke saare fields bharen.", "hi": "कृपया कार्ड के सभी फ़ील्ड भरें।", "bn": "কার্ডের সব ঘর পূরণ করুন।"
};
NOEL_I18N["status.cancel_confirm"] = {
  "en": "Cancel this booking? The cancellation rules on this page apply.",
  "es": "¿Cancelar esta reserva? Se aplican las reglas de cancelación de esta página.",
  "fr": "Annuler cette réservation ? Les règles d'annulation de cette page s'appliquent.",
  "ar": "ألغِ هذا الحجز؟ تنطبق قواعد الإلغاء الموضحة في هذه الصفحة.",
  "pt": "Cancelar esta reserva? As regras de cancelamento desta página se aplicam.",
  "ur": "Ye booking cancel karen? Is page par likhe cancellation rules laagu honge.",
  "hi": "यह बुकिंग रद्द करें? इस पेज पर लिखे रद्दीकरण नियम लागू होंगे।",
  "bn": "এই বুকিং বাতিল করবেন? এই পাতায় লেখা বাতিলের নিয়ম প্রযোজ্য হবে।"
};
NOEL_I18N["status.payment_needed"] = {
  "en": "Payment needed to confirm your ride", "es": "Se necesita el pago para confirmar tu viaje",
  "fr": "Paiement requis pour confirmer votre trajet",
  "ar": "يلزم الدفع لتأكيد رحلتك", "pt": "Pagamento necessário para confirmar sua viagem",
  "ur": "Ride confirm karne ke liye payment zaroori hai", "hi": "आपकी सवारी की पुष्टि के लिए भुगतान आवश्यक है", "bn": "আপনার রাইড নিশ্চিত করতে পেমেন্ট প্রয়োজন"
};
NOEL_I18N["status.chauffeur_confirmed"] = {
  "en": "Chauffeur confirmed", "es": "Chófer confirmado", "fr": "Chauffeur confirmé",
  "ar": "تم تأكيد السائق", "pt": "Motorista confirmado",
  "ur": "Chauffeur confirm ho gaya", "hi": "शॉफ़र कन्फ़र्म हो गया", "bn": "শোফার নিশ্চিত হয়েছে"
};
NOEL_I18N["status.arrived"] = {
  "en": "Your chauffeur has arrived", "es": "Tu chófer ha llegado", "fr": "Votre chauffeur est arrivé",
  "ar": "وصل سائقك", "pt": "Seu motorista chegou",
  "ur": "Aapka chauffeur aa gaya hai", "hi": "आपका शॉफ़र आ गया है", "bn": "আপনার শোফার পৌঁছেছেন"
};
NOEL_I18N["status.under_way"] = {
  "en": "Your ride is under way", "es": "Tu viaje está en curso", "fr": "Votre trajet est en cours",
  "ar": "رحلتك جارية الآن", "pt": "Sua viagem está em andamento",
  "ur": "Aapki ride chal rahi hai", "hi": "आपकी सवारी चल रही है", "bn": "আপনার রাইড চলছে"
};
NOEL_I18N["status.completed_thanks"] = {
  "en": "Ride completed — thank you", "es": "Viaje completado: gracias", "fr": "Trajet terminé — merci",
  "ar": "اكتملت الرحلة — شكرًا لك", "pt": "Viagem concluída — obrigado",
  "ur": "Ride complete ho gayi — shukriya", "hi": "सवारी पूरी हुई — धन्यवाद", "bn": "রাইড সম্পূর্ণ হয়েছে — ধন্যবাদ"
};
NOEL_I18N["status.booking_cancelled"] = {
  "en": "This booking was cancelled", "es": "Esta reserva fue cancelada", "fr": "Cette réservation a été annulée",
  "ar": "تم إلغاء هذا الحجز", "pt": "Esta reserva foi cancelada",
  "ur": "Ye booking cancel ho gayi", "hi": "यह बुकिंग रद्द कर दी गई", "bn": "এই বুকিং বাতিল করা হয়েছে"
};
NOEL_I18N["status.no_show"] = {
  "en": "Marked as a no-show", "es": "Marcado como no presentado", "fr": "Marqué comme absent",
  "ar": "تم تسجيله كعدم حضور", "pt": "Marcado como não comparecimento",
  "ur": "No-show mark kiya gaya", "hi": "नो-शो के रूप में चिह्नित", "bn": "নো-শো হিসেবে চিহ্নিত"
};
NOEL_I18N["status.hours_suffix"] = {
  "en": "hour(s)", "es": "hora(s)", "fr": "heure(s)",
  "ar": "ساعة", "pt": "hora(s)",
  "ur": "hour(s)", "hi": "घंटे", "bn": "ঘণ্টা"
};
NOEL_I18N["status.pickup_label"] = {
  "en": "Pickup", "es": "Recogida", "fr": "Prise en charge",
  "ar": "الاستلام", "pt": "Embarque",
  "ur": "Pickup", "hi": "पिकअप", "bn": "পিকআপ"
};
NOEL_I18N["status.map_unavailable"] = {
  "en": "Live map is unavailable right now. Your chauffeur is on the way to {place}.",
  "es": "El mapa en vivo no está disponible ahora mismo. Tu chófer está en camino a {place}.",
  "fr": "La carte en direct n'est pas disponible pour le moment. Votre chauffeur est en route vers {place}.",
  "ar": "الخريطة المباشرة غير متاحة الآن. سائقك في الطريق إلى {place}.",
  "pt": "O mapa ao vivo não está disponível agora. Seu motorista está a caminho de {place}.",
  "ur": "Live map abhi available nahi hai. Aapka chauffeur {place} ki taraf aa raha hai.",
  "hi": "लाइव मैप अभी उपलब्ध नहीं है। आपका शॉफ़र {place} की ओर आ रहा है।",
  "bn": "লাইভ মানচিত্র এখন উপলব্ধ নয়। আপনার শোফার {place}-এর দিকে আসছেন।"
};
NOEL_I18N["status.map_pickup_point"] = {
  "en": "your pickup point", "es": "tu punto de recogida", "fr": "votre point de prise en charge",
  "ar": "نقطة الاستلام الخاصة بك", "pt": "seu ponto de embarque",
  "ur": "aapka pickup point", "hi": "आपका पिकअप पॉइंट", "bn": "আপনার পিকআপ পয়েন্ট"
};
NOEL_I18N["class.choose_experience"] = {
  "en": "Choose your experience", "es": "Elige tu experiencia", "fr": "Choisissez votre expérience",
  "ar": "اختر تجربتك", "pt": "Escolha sua experiência",
  "ur": "Apna experience chunen", "hi": "अपना अनुभव चुनें", "bn": "আপনার অভিজ্ঞতা বেছে নিন"
};
NOEL_I18N["class.choose_vehicle"] = {
  "en": "Choose your vehicle class", "es": "Elige la clase de tu vehículo",
  "fr": "Choisissez la classe de votre véhicule",
  "ar": "اختر فئة مركبتك", "pt": "Escolha a classe do seu veículo",
  "ur": "Apni gaadi ki class chunen", "hi": "अपने वाहन की श्रेणी चुनें", "bn": "আপনার গাড়ির শ্রেণি বেছে নিন"
};
NOEL_I18N["class.explore"] = {
  "en": "Explore {label} details", "es": "Ver detalles de {label}", "fr": "Découvrir les détails de {label}",
  "ar": "استكشف تفاصيل {label}", "pt": "Ver detalhes de {label}",
  "ur": "{label} ki details dekhen", "hi": "{label} का विवरण देखें", "bn": "{label}-এর বিবরণ দেখুন"
};
NOEL_I18N["class.whats_included"] = {
  "en": "What's included", "es": "Qué incluye", "fr": "Ce qui est inclus",
  "ar": "ما المشمول", "pt": "O que está incluído",
  "ur": "Is mein kya hai", "hi": "इसमें क्या शामिल है", "bn": "কী কী অন্তর্ভুক্ত"
};
NOEL_I18N["class.included_1"] = {
  "en": "Personal meet & greet", "es": "Recibimiento personal", "fr": "Accueil personnalisé",
  "ar": "استقبال شخصي", "pt": "Recepção pessoal",
  "ur": "Personal meet & greet", "hi": "व्यक्तिगत स्वागत", "bn": "ব্যক্তিগত অভ্যর্থনা"
};
NOEL_I18N["class.included_2"] = {
  "en": "Includes up to 15 minutes of free wait time",
  "es": "Incluye hasta 15 minutos de espera gratis",
  "fr": "Jusqu'à 15 minutes d'attente gratuite incluses",
  "ar": "يشمل حتى 15 دقيقة انتظار مجاني",
  "pt": "Inclui até 15 minutos de espera gratuita",
  "ur": "15 minutes tak free wait time shamil hai",
  "hi": "15 मिनट तक मुफ़्त प्रतीक्षा समय शामिल है",
  "bn": "১৫ মিনিট পর্যন্ত বিনামূল্যে অপেক্ষার সময় অন্তর্ভুক্ত"
};
NOEL_I18N["class.included_3"] = {
  "en": "Free to cancel up to 1 hour before pickup",
  "es": "Cancelación gratis hasta 1 hora antes de la recogida",
  "fr": "Annulation gratuite jusqu'à 1 heure avant la prise en charge",
  "ar": "إلغاء مجاني حتى ساعة واحدة قبل الاستلام",
  "pt": "Cancelamento gratuito até 1 hora antes do embarque",
  "ur": "Pickup se 1 hour pehle tak free cancel",
  "hi": "पिकअप से 1 घंटे पहले तक मुफ़्त रद्द करें",
  "bn": "পিকআপের ১ ঘণ্টা আগে পর্যন্ত বিনামূল্যে বাতিল"
};
NOEL_I18N["class.included_4"] = {
  "en": "iOS and Android chargers onboard", "es": "Cargadores para iOS y Android a bordo",
  "fr": "Chargeurs iOS et Android à bord",
  "ar": "شواحن iOS وأندرويد على متن السيارة", "pt": "Carregadores para iOS e Android a bordo",
  "ur": "iOS aur Android chargers onboard", "hi": "iOS और Android चार्जर ऑनबोर्ड", "bn": "iOS ও Android চার্জার অনবোর্ড"
};
NOEL_I18N["class.included_5"] = {
  "en": "Assistance with luggage at pickup and drop-off",
  "es": "Ayuda con el equipaje en la recogida y la llegada",
  "fr": "Aide avec les bagages à la prise en charge et à l'arrivée",
  "ar": "مساعدة في الأمتعة عند الاستلام والوصول",
  "pt": "Ajuda com a bagagem no embarque e no desembarque",
  "ur": "Pickup aur drop-off par luggage mein madad",
  "hi": "पिकअप और ड्रॉप-ऑफ़ पर सामान में सहायता",
  "bn": "পিকআপ ও ড্রপ-অফে লাগেজে সাহায্য"
};
NOEL_I18N["class.capacity"] = {
  "en": "Capacity", "es": "Capacidad", "fr": "Capacité",
  "ar": "السعة", "pt": "Capacidade",
  "ur": "Capacity", "hi": "क्षमता", "bn": "ধারণক্ষমতা"
};
NOEL_I18N["class.luggage"] = {
  "en": "Luggage", "es": "Equipaje", "fr": "Bagages",
  "ar": "الأمتعة", "pt": "Bagagem",
  "ur": "Luggage", "hi": "सामान", "bn": "লাগেজ"
};
NOEL_I18N["class.seating"] = {
  "en": "Seating", "es": "Asientos", "fr": "Places",
  "ar": "المقاعد", "pt": "Assentos",
  "ur": "Seating", "hi": "सीटें", "bn": "আসন"
};
NOEL_I18N["class.passengers"] = {
  "en": "{n} passengers", "es": "{n} pasajeros", "fr": "{n} passagers",
  "ar": "{n} ركاب", "pt": "{n} passageiros",
  "ur": "{n} passengers", "hi": "{n} यात्री", "bn": "{n} জন যাত্রী"
};
NOEL_I18N["class.breakdown"] = {
  "en": "Price breakdown", "es": "Desglose del precio", "fr": "Détail du prix",
  "ar": "تفصيل السعر", "pt": "Detalhamento do preço",
  "ur": "Price breakdown", "hi": "मूल्य विवरण", "bn": "মূল্যের বিবরণ"
};
NOEL_I18N["class.base_fare"] = {
  "en": "Base fare", "es": "Tarifa base", "fr": "Tarif de base",
  "ar": "الأجرة الأساسية", "pt": "Tarifa base",
  "ur": "Base fare", "hi": "आधार किराया", "bn": "মূল ভাড়া"
};
NOEL_I18N["class.airport_fee"] = {
  "en": "Airport access fee", "es": "Tasa de acceso al aeropuerto", "fr": "Frais d'accès à l'aéroport",
  "ar": "رسوم دخول المطار", "pt": "Taxa de acesso ao aeroporto",
  "ur": "Airport access fee", "hi": "एयरपोर्ट प्रवेश शुल्क", "bn": "বিমানবন্দর প্রবেশ ফি"
};
NOEL_I18N["class.black_car_fee"] = {
  "en": "Black car fee", "es": "Tasa de coche negro", "fr": "Frais de voiture noire",
  "ar": "رسوم السيارة السوداء", "pt": "Taxa de carro preto",
  "ur": "Black car fee", "hi": "ब्लैक कार शुल्क", "bn": "ব্ল্যাক কার ফি"
};
NOEL_I18N["class.sales_tax"] = {
  "en": "Sales tax", "es": "Impuesto sobre las ventas", "fr": "Taxe de vente",
  "ar": "ضريبة المبيعات", "pt": "Imposto sobre vendas",
  "ur": "Sales tax", "hi": "बिक्री कर", "bn": "বিক্রয় কর"
};
NOEL_I18N["class.congestion"] = {
  "en": "Congestion", "es": "Congestión", "fr": "Congestion",
  "ar": "ازدحام", "pt": "Congestionamento",
  "ur": "Congestion", "hi": "भीड़ शुल्क", "bn": "যানজট"
};
NOEL_I18N["class.toll"] = {
  "en": "Toll", "es": "Peaje", "fr": "Péage",
  "ar": "رسوم الطرق", "pt": "Pedágio",
  "ur": "Toll", "hi": "टोल", "bn": "টোল"
};
NOEL_I18N["class.total"] = {
  "en": "Total", "es": "Total", "fr": "Total",
  "ar": "المجموع", "pt": "Total",
  "ur": "Total", "hi": "कुल", "bn": "মোট"
};
NOEL_I18N["class.please_note"] = {
  "en": "Please note", "es": "Ten en cuenta", "fr": "Veuillez noter",
  "ar": "يرجى الملاحظة", "pt": "Observação",
  "ur": "Please note", "hi": "कृपया ध्यान दें", "bn": "অনুগ্রহ করে লক্ষ্য করুন"
};
NOEL_I18N["class.note_1"] = {
  "en": "Your estimated total fare is based on the trip details shown above. The final fare may change if you change the pickup or drop-off location, change the vehicle type, or a different route is taken.",
  "es": "La tarifa total estimada se basa en los detalles del viaje mostrados arriba. La tarifa final puede cambiar si cambias el lugar de recogida o destino, el tipo de vehículo o si se toma otra ruta.",
  "fr": "Le tarif total estimé est basé sur les détails du trajet ci-dessus. Le tarif final peut changer si vous modifiez le lieu de prise en charge ou de destination, le type de véhicule, ou si un autre itinéraire est emprunté.",
  "ar": "الأجرة الإجمالية التقديرية مبنية على تفاصيل الرحلة أعلاه. قد تتغير الأجرة النهائية إذا غيّرت مكان الاستلام أو الوصول أو نوع المركبة أو سُلك طريق مختلف.",
  "pt": "A tarifa total estimada baseia-se nos detalhes da viagem acima. A tarifa final pode mudar se você alterar o local de embarque ou destino, o tipo de veículo ou se outra rota for seguida.",
  "ur": "Aapka estimated total fare upar dikhaye gaye trip details par hai. Final fare badal sakta hai agar aap pickup ya drop-off jagah, gaadi ki type badal dein ya koi doosra route liya jaye.",
  "hi": "आपका अनुमानित कुल किराया ऊपर दिखाए गए यात्रा विवरण पर आधारित है। अंतिम किराया बदल सकता है यदि आप पिकअप या ड्रॉप-ऑफ़ स्थान, वाहन का प्रकार बदलते हैं या कोई दूसरा रास्ता लिया जाता है।",
  "bn": "আপনার আনুমানিক মোট ভাড়া উপরে দেখানো ট্রিপের বিবরণের ভিত্তিতে। পিকআপ বা ড্রপ-অফের জায়গা, গাড়ির ধরন বদলালে বা অন্য রুট নিলে চূড়ান্ত ভাড়া বদলে যেতে পারে।"
};
NOEL_I18N["class.note_2"] = {
  "en": "Guest and luggage capacities must be respected for safety reasons. If you are unsure, select a larger class.",
  "es": "Por seguridad, se deben respetar las capacidades de pasajeros y equipaje. Si no estás seguro, elige una clase mayor.",
  "fr": "Pour des raisons de sécurité, les capacités en passagers et en bagages doivent être respectées. En cas de doute, choisissez une classe supérieure.",
  "ar": "يجب احترام سعة الركاب والأمتعة لأسباب تتعلق بالسلامة. إذا لم تكن متأكدًا، فاختر فئة أكبر.",
  "pt": "Por segurança, as capacidades de passageiros e bagagem devem ser respeitadas. Se não tiver certeza, escolha uma classe maior.",
  "ur": "Safety ke liye guest aur luggage ki capacity ka khayal rakhen. Agar sure nahi hain to badi class chunen.",
  "hi": "सुरक्षा के लिए यात्रियों और सामान की क्षमता का सम्मान करें। यदि अनिश्चित हैं, तो बड़ी श्रेणी चुनें।",
  "bn": "নিরাপত্তার জন্য যাত্রী ও লাগেজের ধারণক্ষমতা মেনে চলুন। নিশ্চিত না হলে বড় শ্রেণি বেছে নিন।"
};
NOEL_I18N["class.note_3"] = {
  "en": "The vehicle images above are examples. You may get a different vehicle of similar quality.",
  "es": "Las imágenes de los vehículos son ejemplos. Es posible que recibas un vehículo diferente de calidad similar.",
  "fr": "Les images des véhicules ci-dessus sont des exemples. Vous pouvez recevoir un véhicule différent de qualité similaire.",
  "ar": "صور المركبات أعلاه أمثلة فقط. قد تحصل على مركبة مختلفة بجودة مماثلة.",
  "pt": "As imagens dos veículos acima são exemplos. Você pode receber um veículo diferente de qualidade similar.",
  "ur": "Upar dikhayi gayi gaadiyon ki photos examples hain. Aapko same quality ki koi doosri gaadi mil sakti hai.",
  "hi": "ऊपर दिखाए गए वाहनों की तस्वीरें उदाहरण हैं। आपको समान गुणवत्ता वाला कोई दूसरा वाहन मिल सकता है।",
  "bn": "উপরের গাড়ির ছবিগুলো উদাহরণ মাত্র। আপনি একই মানের অন্য গাড়ি পেতে পারেন।"
};
NOEL_I18N["class.select"] = {
  "en": "Select {label}", "es": "Seleccionar {label}", "fr": "Choisir {label}",
  "ar": "اختر {label}", "pt": "Selecionar {label}",
  "ur": "{label} select karen", "hi": "{label} चुनें", "bn": "{label} বেছে নিন"
};
NOEL_I18N["class.your_details"] = {
  "en": "Your details", "es": "Tus datos", "fr": "Vos coordonnées",
  "ar": "بياناتك", "pt": "Seus dados",
  "ur": "Aapki details", "hi": "आपका विवरण", "bn": "আপনার বিবরণ"
};
NOEL_I18N["class.your_name"] = {
  "en": "Your name", "es": "Tu nombre", "fr": "Votre nom",
  "ar": "اسمك", "pt": "Seu nome",
  "ur": "Aapka naam", "hi": "आपका नाम", "bn": "আপনার নাম"
};
NOEL_I18N["class.phone"] = {
  "en": "Phone number", "es": "Número de teléfono", "fr": "Numéro de téléphone",
  "ar": "رقم الهاتف", "pt": "Número de telefone",
  "ur": "Phone number", "hi": "फ़ोन नंबर", "bn": "ফোন নম্বর"
};
NOEL_I18N["class.email"] = {
  "en": "Email", "es": "Correo electrónico", "fr": "E-mail",
  "ar": "البريد الإلكتروني", "pt": "E-mail",
  "ur": "Email", "hi": "ईमेल", "bn": "ইমেইল"
};
NOEL_I18N["class.signin_expired"] = {
  "en": "Your sign-in expired — please tap Continue again.",
  "es": "Tu sesión caducó. Toca Continuar de nuevo.",
  "fr": "Votre connexion a expiré — veuillez appuyer à nouveau sur Continuer.",
  "ar": "انتهت صلاحية تسجيل دخولك — يرجى الضغط على متابعة مرة أخرى.",
  "pt": "Sua sessão expirou — toque em Continuar novamente.",
  "ur": "Aapka sign-in expire ho gaya — dobara Continue dabayen.",
  "hi": "आपका साइन-इन समाप्त हो गया — कृपया फिर से जारी रखें दबाएँ।",
  "bn": "আপনার সাইন-ইন মেয়াদ শেষ হয়েছে — আবার চালিয়ে যান চাপুন।"
};
NOEL_I18N["class.details_failed"] = {
  "en": "Your details could not be saved. Please try again.",
  "es": "No se pudieron guardar tus datos. Inténtalo de nuevo.",
  "fr": "Vos coordonnées n'ont pas pu être enregistrées. Veuillez réessayer.",
  "ar": "تعذّر حفظ بياناتك. يرجى المحاولة مرة أخرى.",
  "pt": "Não foi possível salvar seus dados. Tente novamente.",
  "ur": "Aapki details save nahi ho saki. Dobara try karen.",
  "hi": "आपका विवरण सहेजा नहीं जा सका। कृपया फिर से प्रयास करें।",
  "bn": "আপনার বিবরণ সংরক্ষণ করা যায়নি। আবার চেষ্টা করুন।"
};
NOEL_I18N["class.select_failed"] = {
  "en": "That class could not be selected. Please try again.",
  "es": "No se pudo seleccionar esa clase. Inténtalo de nuevo.",
  "fr": "Cette classe n'a pas pu être sélectionnée. Veuillez réessayer.",
  "ar": "تعذّر اختيار هذه الفئة. يرجى المحاولة مرة أخرى.",
  "pt": "Não foi possível selecionar essa classe. Tente novamente.",
  "ur": "Wo class select nahi ho saki. Dobara try karen.",
  "hi": "वह श्रेणी चुनी नहीं जा सकी। कृपया फिर से प्रयास करें।",
  "bn": "সেই শ্রেণিটি নির্বাচন করা যায়নি। আবার চেষ্টা করুন।"
};
NOEL_I18N["class.signin_failed"] = {
  "en": "Sign-in did not work. Please try again.",
  "es": "El inicio de sesión no funcionó. Inténtalo de nuevo.",
  "fr": "La connexion n'a pas fonctionné. Veuillez réessayer.",
  "ar": "لم ينجح تسجيل الدخول. يرجى المحاولة مرة أخرى.",
  "pt": "O login não funcionou. Tente novamente.",
  "ur": "Sign-in kaam nahi kiya. Dobara try karen.",
  "hi": "साइन-इन काम नहीं किया। कृपया फिर से प्रयास करें।",
  "bn": "সাইন-ইন কাজ করেনি। আবার চেষ্টা করুন।"
};
NOEL_I18N["class.unreachable"] = {
  "en": "Could not reach the booking service. Please try again.",
  "es": "No se pudo contactar con el servicio de reservas. Inténtalo de nuevo.",
  "fr": "Impossible de joindre le service de réservation. Veuillez réessayer.",
  "ar": "تعذّر الوصول إلى خدمة الحجز. يرجى المحاولة مرة أخرى.",
  "pt": "Não foi possível acessar o serviço de reservas. Tente novamente.",
  "ur": "Booking service se rabta nahi ho saka. Dobara try karen.",
  "hi": "बुकिंग सेवा से संपर्क नहीं हो सका। कृपया फिर से प्रयास करें।",
  "bn": "বুকিং পরিষেবার সঙ্গে যোগাযোগ করা যায়নি। আবার চেষ্টা করুন।"
};
NOEL_I18N["class.unreachable_conn"] = {
  "en": "Could not reach the booking service. Please check your connection and try again.",
  "es": "No se pudo contactar con el servicio de reservas. Revisa tu conexión e inténtalo de nuevo.",
  "fr": "Impossible de joindre le service de réservation. Vérifiez votre connexion et réessayez.",
  "ar": "تعذّر الوصول إلى خدمة الحجز. يرجى التحقق من اتصالك والمحاولة مرة أخرى.",
  "pt": "Não foi possível acessar o serviço de reservas. Verifique sua conexão e tente novamente.",
  "ur": "Booking service se rabta nahi ho saka. Apna connection check karke dobara try karen.",
  "hi": "बुकिंग सेवा से संपर्क नहीं हो सका। कृपया अपना कनेक्शन जाँचें और फिर से प्रयास करें।",
  "bn": "বুকিং পরিষেবার সঙ্গে যোগাযোগ করা যায়নি। আপনার সংযোগ দেখে আবার চেষ্টা করুন।"
};
NOEL_I18N["class.wrong"] = {
  "en": "Something went wrong. Please try again.",
  "es": "Algo salió mal. Inténtalo de nuevo.",
  "fr": "Une erreur s'est produite. Veuillez réessayer.",
  "ar": "حدث خطأ ما. يرجى المحاولة مرة أخرى.",
  "pt": "Algo deu errado. Tente novamente.",
  "ur": "Kuch ghalat ho gaya. Dobara try karen.",
  "hi": "कुछ गलत हो गया। कृपया फिर से प्रयास करें।",
  "bn": "কিছু ভুল হয়েছে। আবার চেষ্টা করুন।"
};

/* ---- Status / payment / invoice ---- */
NOEL_I18N["status.finding"] = {
  "en": "Finding your chauffeur…", "es": "Buscando tu chófer…", "fr": "Recherche de votre chauffeur…",
  "ar": "جارٍ البحث عن سائقك…", "pt": "Procurando seu motorista…",
  "ur": "Aapka chauffeur dhoondha ja raha hai…", "hi": "आपका शॉफ़र खोजा जा रहा है…", "bn": "আপনার শোফার খোঁজা হচ্ছে…"
};
NOEL_I18N["status.request_with_us"] = {
  "en": "Your request is with us. Please keep this page open.",
  "es": "Tu solicitud está con nosotros. Mantén esta página abierta.",
  "fr": "Votre demande est bien reçue. Veuillez garder cette page ouverte.",
  "ar": "طلبك لدينا. يرجى إبقاء هذه الصفحة مفتوحة.",
  "pt": "Sua solicitação está conosco. Mantenha esta página aberta.",
  "ur": "Aapki request hamare paas hai. Ye page khula rakhen.",
  "hi": "आपका अनुरोध हमारे पास है। कृपया यह पेज खुला रखें।",
  "bn": "আপনার অনুরোধ আমাদের কাছে আছে। এই পাতাটি খোলা রাখুন।"
};
NOEL_I18N["status.confirmed"] = {
  "en": "Your chauffeur is confirmed", "es": "Tu chófer está confirmado",
  "fr": "Votre chauffeur est confirmé",
  "ar": "تم تأكيد سائقك", "pt": "Seu motorista está confirmado",
  "ur": "Aapka chauffeur confirm ho gaya", "hi": "आपका शॉफ़र कन्फ़र्म हो गया", "bn": "আপনার শোফার নিশ্চিত হয়েছে"
};
NOEL_I18N["status.on_the_way"] = {
  "en": "Your chauffeur is on the way.", "es": "Tu chófer está en camino.",
  "fr": "Votre chauffeur est en route.",
  "ar": "سائقك في الطريق إليك.", "pt": "Seu motorista está a caminho.",
  "ur": "Aapka chauffeur raaste mein hai.", "hi": "आपका शॉफ़र रास्ते में है।", "bn": "আপনার শোফার পথে আছেন।"
};
NOEL_I18N["status.details_sent"] = {
  "en": "These details were also sent to your phone and email.",
  "es": "Estos datos también se enviaron a tu teléfono y correo electrónico.",
  "fr": "Ces informations ont également été envoyées sur votre téléphone et par e-mail.",
  "ar": "تم إرسال هذه التفاصيل أيضًا إلى هاتفك وبريدك الإلكتروني.",
  "pt": "Esses dados também foram enviados para seu telefone e e-mail.",
  "ur": "Ye details aapke phone aur email par bhi bheji gayi hain.",
  "hi": "ये जानकारी आपके फ़ोन और ईमेल पर भी भेजी गई है।",
  "bn": "এই বিবরণ আপনার ফোন ও ইমেইলেও পাঠানো হয়েছে।"
};
NOEL_I18N["status.on_the_way_heading"] = {
  "en": "Your chauffeur on the way", "es": "Tu chófer en camino",
  "fr": "Votre chauffeur en route",
  "ar": "سائقك في الطريق", "pt": "Seu motorista a caminho",
  "ur": "Aapka chauffeur raaste mein", "hi": "आपका शॉफ़र रास्ते में", "bn": "আপনার শোফার পথে"
};
NOEL_I18N["status.total_ready"] = {
  "en": "Your total is ready", "es": "Tu total está listo",
  "fr": "Votre total est prêt",
  "ar": "المجموع جاهز", "pt": "Seu total está pronto",
  "ur": "Aapka total ready hai", "hi": "आपका कुल तैयार है", "bn": "আপনার মোট তৈরি"
};
NOEL_I18N["status.pay_below"] = {
  "en": "Please pay by card below — your chauffeur will be assigned right after payment.",
  "es": "Paga con tarjeta abajo: tu chófer será asignado justo después del pago.",
  "fr": "Veuillez payer par carte ci-dessous — votre chauffeur sera assigné juste après le paiement.",
  "ar": "يرجى الدفع بالبطاقة أدناه — وسيتم تعيين سائقك مباشرة بعد الدفع.",
  "pt": "Pague com cartão abaixo — seu motorista será designado logo após o pagamento.",
  "ur": "Neeche card se pay karen — payment ke foran baad aapka chauffeur assign ho jayega.",
  "hi": "कृपया नीचे कार्ड से भुगतान करें — भुगतान के तुरंत बाद आपका शॉफ़र नियुक्त हो जाएगा।",
  "bn": "নিচে কার্ড দিয়ে পেমেন্ট করুন — পেমেন্টের পরপরই আপনার শোফার নিয়োগ করা হবে।"
};
NOEL_I18N["status.your_total"] = {
  "en": "Your total", "es": "Tu total", "fr": "Votre total",
  "ar": "المجموع الخاص بك", "pt": "Seu total",
  "ur": "Aapka total", "hi": "आपका कुल", "bn": "আপনার মোট"
};
NOEL_I18N["status.one_total"] = {
  "en": "One single total for your ride. No breakdown, no hidden charges.",
  "es": "Un solo total para tu viaje. Sin desglose ni cargos ocultos.",
  "fr": "Un seul total pour votre trajet. Aucun détail, aucun frais caché.",
  "ar": "مجموع واحد لرحلتك. لا تفصيل ولا رسوم خفية.",
  "pt": "Um único total para sua viagem. Sem detalhamento, sem taxas ocultas.",
  "ur": "Aapki ride ka ek hi total. Na breakdown, na chhupe hue charges.",
  "hi": "आपकी सवारी का एक ही कुल। कोई विवरण नहीं, कोई छिपा शुल्क नहीं।",
  "bn": "আপনার রাইডের একটাই মোট। কোনো বিবরণ নেই, কোনো লুকানো চার্জ নেই।"
};
NOEL_I18N["status.pay_by_card"] = {
  "en": "Pay by card", "es": "Pagar con tarjeta", "fr": "Payer par carte",
  "ar": "ادفع بالبطاقة", "pt": "Pagar com cartão",
  "ur": "Card se pay karen", "hi": "कार्ड से भुगतान करें", "bn": "কার্ড দিয়ে পেমেন্ট করুন"
};
NOEL_I18N["status.card_unavailable"] = {
  "en": "Card payments are not set up yet. Please try again later.",
  "es": "Los pagos con tarjeta aún no están configurados. Inténtalo más tarde.",
  "fr": "Les paiements par carte ne sont pas encore configurés. Veuillez réessayer plus tard.",
  "ar": "الدفع بالبطاقة غير مُعدّ بعد. يرجى المحاولة لاحقًا.",
  "pt": "Pagamentos com cartão ainda não estão configurados. Tente novamente mais tarde.",
  "ur": "Card payments abhi set nahi hain. Thodi der mein dobara try karen.",
  "hi": "कार्ड भुगतान अभी सेट नहीं है। कृपया बाद में फिर से प्रयास करें।",
  "bn": "কার্ড পেমেন্ট এখনো চালু হয়নি। পরে আবার চেষ্টা করুন।"
};
NOEL_I18N["status.loading_payment"] = {
  "en": "Loading secure payment…", "es": "Cargando el pago seguro…", "fr": "Chargement du paiement sécurisé…",
  "ar": "جارٍ تحميل الدفع الآمن…", "pt": "Carregando pagamento seguro…",
  "ur": "Secure payment load ho raha hai…", "hi": "सुरक्षित भुगतान लोड हो रहा है…", "bn": "নিরাপদ পেমেন্ট লোড হচ্ছে…"
};
NOEL_I18N["status.test_mode"] = {
  "en": "TEST MODE — no real charge.", "es": "MODO DE PRUEBA: sin cargo real.",
  "fr": "MODE TEST — aucun débit réel.",
  "ar": "وضع الاختبار — لا يوجد خصم حقيقي.", "pt": "MODO DE TESTE — sem cobrança real.",
  "ur": "TEST MODE — koi real charge nahi.", "hi": "टेस्ट मोड — कोई असली शुल्क नहीं।", "bn": "টেস্ট মোড — কোনো আসল চার্জ নেই।"
};
NOEL_I18N["status.test_note"] = {
  "en": "This payment form is in test mode. No real payment will be taken from your card.",
  "es": "Este formulario de pago está en modo de prueba. No se cobrará nada real de tu tarjeta.",
  "fr": "Ce formulaire de paiement est en mode test. Aucun paiement réel ne sera prélevé sur votre carte.",
  "ar": "نموذج الدفع هذا في وضع الاختبار. لن يتم خصم أي مبلغ حقيقي من بطاقتك.",
  "pt": "Este formulário de pagamento está em modo de teste. Nenhum pagamento real será cobrado do seu cartão.",
  "ur": "Ye payment form test mode mein hai. Aapke card se koi real payment nahi liya jayega.",
  "hi": "यह भुगतान फ़ॉर्म टेस्ट मोड में है। आपके कार्ड से कोई असली भुगतान नहीं लिया जाएगा।",
  "bn": "এই পেমেন্ট ফর্মটি টেস্ট মোডে আছে। আপনার কার্ড থেকে কোনো আসল পেমেন্ট নেওয়া হবে না।"
};
NOEL_I18N["status.card_name"] = {
  "en": "Name on card", "es": "Nombre en la tarjeta", "fr": "Nom sur la carte",
  "ar": "الاسم على البطاقة", "pt": "Nome no cartão",
  "ur": "Card par naam", "hi": "कार्ड पर नाम", "bn": "কার্ডে নাম"
};
NOEL_I18N["status.card_number"] = {
  "en": "Card number", "es": "Número de tarjeta", "fr": "Numéro de carte",
  "ar": "رقم البطاقة", "pt": "Número do cartão",
  "ur": "Card number", "hi": "कार्ड नंबर", "bn": "কার্ড নম্বর"
};
NOEL_I18N["status.expiry"] = {
  "en": "Expiry (MM/YY)", "es": "Vencimiento (MM/AA)", "fr": "Expiration (MM/AA)",
  "ar": "تاريخ الانتهاء (شهر/سنة)", "pt": "Validade (MM/AA)",
  "ur": "Expiry (MM/YY)", "hi": "समाप्ति (माह/वर्ष)", "bn": "মেয়াদ (মাস/বছর)"
};
NOEL_I18N["status.cvc"] = {
  "en": "CVC", "es": "CVC", "fr": "CVC",
  "ar": "رمز الأمان", "pt": "CVC",
  "ur": "CVC", "hi": "CVC", "bn": "CVC"
};
NOEL_I18N["status.invoice"] = {
  "en": "Your invoice", "es": "Tu factura", "fr": "Votre facture",
  "ar": "فاتورتك", "pt": "Sua fatura",
  "ur": "Aapka invoice", "hi": "आपका चालान", "bn": "আপনার চালান"
};
NOEL_I18N["status.ride_total"] = {
  "en": "Ride total", "es": "Total del viaje", "fr": "Total du trajet",
  "ar": "إجمالي الرحلة", "pt": "Total da viagem",
  "ur": "Ride total", "hi": "सवारी का कुल", "bn": "রাইডের মোট"
};
NOEL_I18N["status.waiting"] = {
  "en": "Waiting charge", "es": "Cargo por espera", "fr": "Frais d'attente",
  "ar": "رسوم الانتظار", "pt": "Taxa de espera",
  "ur": "Waiting charge", "hi": "प्रतीक्षा शुल्क", "bn": "অপেক্ষার চার্জ"
};
NOEL_I18N["status.extra_distance"] = {
  "en": "Extra distance", "es": "Distancia extra", "fr": "Distance supplémentaire",
  "ar": "مسافة إضافية", "pt": "Distância extra",
  "ur": "Extra distance", "hi": "अतिरिक्त दूरी", "bn": "অতিরিক্ত দূরত্ব"
};
NOEL_I18N["status.amount_paid"] = {
  "en": "Amount paid", "es": "Cantidad pagada", "fr": "Montant payé",
  "ar": "المبلغ المدفوع", "pt": "Valor pago",
  "ur": "Amount paid", "hi": "भुगतान की गई राशि", "bn": "পরিশোধিত অর্থ"
};
NOEL_I18N["status.invoice_sent"] = {
  "en": "Your invoice has been sent to your phone and email.",
  "es": "Tu factura se ha enviado a tu teléfono y correo electrónico.",
  "fr": "Votre facture a été envoyée sur votre téléphone et par e-mail.",
  "ar": "تم إرسال فاتورتك إلى هاتفك وبريدك الإلكتروني.",
  "pt": "Sua fatura foi enviada para seu telefone e e-mail.",
  "ur": "Aapka invoice aapke phone aur email par bhej diya gaya hai.",
  "hi": "आपका चालान आपके फ़ोन और ईमेल पर भेज दिया गया है।",
  "bn": "আপনার চালান আপনার ফোন ও ইমেইলে পাঠানো হয়েছে।"
};
NOEL_I18N["status.chat_with_chauffeur"] = {
  "en": "Chat with your chauffeur", "es": "Chatea con tu chófer", "fr": "Discutez avec votre chauffeur",
  "ar": "تحدث مع سائقك", "pt": "Converse com seu motorista",
  "ur": "Apne chauffeur se chat karen", "hi": "अपने शॉफ़र से चैट करें", "bn": "আপনার শোফারের সঙ্গে চ্যাট করুন"
};
NOEL_I18N["status.chat_language_label"] = {
  "en": "Language", "es": "Idioma", "fr": "Langue",
  "ar": "اللغة", "pt": "Idioma",
  "ur": "Language", "hi": "भाषा", "bn": "ভাষা"
};
NOEL_I18N["status.chat_input_ph"] = {
  "en": "Write a message…", "es": "Escribe un mensaje…", "fr": "Écrivez un message…",
  "ar": "اكتب رسالة…", "pt": "Escreva uma mensagem…",
  "ur": "Message likhen…", "hi": "संदेश लिखें…", "bn": "বার্তা লিখুন…"
};
NOEL_I18N["status.plate"] = {
  "en": "Plate", "es": "Matrícula", "fr": "Plaque",
  "ar": "اللوحة", "pt": "Placa",
  "ur": "Plate", "hi": "नंबर प्लेट", "bn": "নম্বর প্লেট"
};
NOEL_I18N["status.phone_label"] = {
  "en": "Phone", "es": "Teléfono", "fr": "Téléphone",
  "ar": "الهاتف", "pt": "Telefone",
  "ur": "Phone", "hi": "फ़ोन", "bn": "ফোন"
};
NOEL_I18N["status.thankyou"] = {
  "en": "Thank you — your ride is booked.", "es": "Gracias, tu viaje está reservado.",
  "fr": "Merci — votre trajet est réservé.",
  "ar": "شكرًا لك — تم حجز رحلتك.", "pt": "Obrigado — sua viagem está reservada.",
  "ur": "Shukriya — aapki ride book ho gayi.", "hi": "धन्यवाद — आपकी सवारी बुक हो गई।", "bn": "ধন্যবাদ — আপনার রাইড বুক হয়েছে।"
};
NOEL_I18N["status.stripe_hold_note"] = {
  "en": "Your card is charged as a hold when you book. Your card details go directly to Stripe — they are never typed into, or stored on, this site.",
  "es": "Tu tarjeta se carga como retención al reservar. Los datos de tu tarjeta van directamente a Stripe: nunca se escriben ni se guardan en este sitio.",
  "fr": "Votre carte est débitée à titre de garantie lors de la réservation. Les données de votre carte vont directement à Stripe — elles ne sont jamais saisies ni stockées sur ce site.",
  "ar": "يتم خصم مبلغ من بطاقتك كحجز عند الحجز. تذهب بيانات بطاقتك مباشرة إلى Stripe — ولا تُكتب أو تُحفظ أبدًا على هذا الموقع.",
  "pt": "Seu cartão é cobrado como retenção ao reservar. Os dados do seu cartão vão diretamente para a Stripe — nunca são digitados ou armazenados neste site.",
  "ur": "Book karte waqt aapke card par hold lagaya jata hai. Aapke card ki details seedha Stripe ko jati hain — wo is site par na likhi jati hain na save hoti hain.",
  "hi": "बुक करते समय आपके कार्ड पर होल्ड लगाया जाता है। आपके कार्ड का विवरण सीधे Stripe को जाता है — यह इस साइट पर न तो लिखा जाता है और न ही सहेजा जाता है।",
  "bn": "বুক করার সময় আপনার কার্ডে হোল্ড চার্জ করা হয়। আপনার কার্ডের বিবরণ সরাসরি Stripe-এ যায় — এগুলো এই সাইটে কখনো লেখা বা সংরক্ষণ করা হয় না।"
};
NOEL_I18N["status.saved_cards"] = {
  "en": "Your saved cards", "es": "Tus tarjetas guardadas", "fr": "Vos cartes enregistrées",
  "ar": "بطاقاتك المحفوظة", "pt": "Seus cartões salvos",
  "ur": "Aapke saved cards", "hi": "आपके सहेजे गए कार्ड", "bn": "আপনার সংরক্ষিত কার্ড"
};
NOEL_I18N["status.card_details"] = {
  "en": "Card details", "es": "Datos de la tarjeta", "fr": "Détails de la carte",
  "ar": "بيانات البطاقة", "pt": "Dados do cartão",
  "ur": "Card details", "hi": "कार्ड विवरण", "bn": "কার্ডের বিবরণ"
};
NOEL_I18N["status.save_card"] = {
  "en": "Save this card for future rides", "es": "Guardar esta tarjeta para futuros viajes",
  "fr": "Enregistrer cette carte pour vos prochains trajets",
  "ar": "احفظ هذه البطاقة للرحلات القادمة", "pt": "Salvar este cartão para viagens futuras",
  "ur": "Aage ki rides ke liye ye card save karen", "hi": "भविष्य की सवारियों के लिए यह कार्ड सहेजें", "bn": "ভবিষ্যতের রাইডের জন্য এই কার্ড সংরক্ষণ করুন"
};
NOEL_I18N["status.test_mode_short"] = {
  "en": "Test mode — no real charge.", "es": "Modo de prueba: sin cargo real.",
  "fr": "Mode test — aucun débit réel.",
  "ar": "وضع الاختبار — لا يوجد خصم حقيقي.", "pt": "Modo de teste — sem cobrança real.",
  "ur": "Test mode — koi real charge nahi.", "hi": "टेस्ट मोड — कोई असली शुल्क नहीं।", "bn": "টেস্ট মোড — কোনো আসল চার্জ নেই।"
};
NOEL_I18N["status.test_booking_rest"] = {
  "en": "This booking was paid in test mode; no real payment was taken.",
  "es": "Esta reserva se pagó en modo de prueba; no se cobró nada real.",
  "fr": "Cette réservation a été payée en mode test ; aucun paiement réel n'a été prélevé.",
  "ar": "تم دفع هذا الحجز في وضع الاختبار؛ ولم يتم خصم أي مبلغ حقيقي.",
  "pt": "Esta reserva foi paga em modo de teste; nenhum pagamento real foi cobrado.",
  "ur": "Ye booking test mode mein pay hui; koi real payment nahi liya gaya.",
  "hi": "यह बुकिंग टेस्ट मोड में भुगतान की गई; कोई असली भुगतान नहीं लिया गया।",
  "bn": "এই বুকিং টেস্ট মোডে পে করা হয়েছে; কোনো আসল পেমেন্ট নেওয়া হয়নি।"
};
NOEL_I18N["status.cancel_booking"] = {
  "en": "Cancel this booking", "es": "Cancelar esta reserva", "fr": "Annuler cette réservation",
  "ar": "ألغِ هذا الحجز", "pt": "Cancelar esta reserva",
  "ur": "Ye booking cancel karen", "hi": "यह बुकिंग रद्द करें", "bn": "এই বুকিং বাতিল করুন"
};
NOEL_I18N["status.return_trip"] = {
  "en": "Your return trip", "es": "Tu viaje de regreso", "fr": "Votre trajet retour",
  "ar": "رحلة عودتك", "pt": "Sua viagem de volta",
  "ur": "Aapki return trip", "hi": "आपकी वापसी यात्रा", "bn": "আপনার ফেরার যাত্রা"
};
NOEL_I18N["status.another_ride"] = {
  "en": "Another ride", "es": "Otro viaje", "fr": "Un autre trajet",
  "ar": "رحلة أخرى", "pt": "Outra viagem",
  "ur": "Ek aur ride", "hi": "एक और सवारी", "bn": "আরেকটি রাইড"
};
NOEL_I18N["status.test_booking_note"] = {
  "en": "Test mode — no real charge. This booking was paid in test mode; no real payment was taken.",
  "es": "Modo de prueba: sin cargo real. Esta reserva se pagó en modo de prueba; no se cobró nada real.",
  "fr": "Mode test — aucun débit réel. Cette réservation a été payée en mode test ; aucun paiement réel n'a été prélevé.",
  "ar": "وضع الاختبار — لا يوجد خصم حقيقي. تم دفع هذا الحجز في وضع الاختبار؛ ولم يتم خصم أي مبلغ حقيقي.",
  "pt": "Modo de teste — sem cobrança real. Esta reserva foi paga em modo de teste; nenhum pagamento real foi cobrado.",
  "ur": "Test mode — koi real charge nahi. Ye booking test mode mein pay hui; koi real payment nahi liya gaya.",
  "hi": "टेस्ट मोड — कोई असली शुल्क नहीं। यह बुकिंग टेस्ट मोड में भुगतान की गई; कोई असली भुगतान नहीं लिया गया।",
  "bn": "টেস্ট মোড — কোনো আসল চার্জ নেই। এই বুকিং টেস্ট মোডে পে করা হয়েছে; কোনো আসল পেমেন্ট নেওয়া হয়নি।"
};

/* ---- Homepage sections ---- */
NOEL_I18N["home.travel_terms"] = {
  "en": "Travel on your own terms.", "es": "Viaja a tu manera.", "fr": "Voyagez à votre façon.",
  "ar": "سافر بشروطك الخاصة.", "pt": "Viaje do seu jeito.",
  "ur": "Apni marzi se safar karen.", "hi": "अपनी शर्तों पर यात्रा करें।", "bn": "নিজের মতো করে ভ্রমণ করুন।"
};
NOEL_I18N["home.travel_terms_p"] = {
  "en": "Premium service, absolute privacy and seamless journeys.",
  "es": "Servicio premium, privacidad absoluta y viajes sin complicaciones.",
  "fr": "Service premium, confidentialité absolue et trajets sans accroc.",
  "ar": "خدمة مميزة وخصوصية تامة ورحلات سلسة.",
  "pt": "Serviço premium, privacidade absoluta e viagens sem complicações.",
  "ur": "Premium service, poori privacy aur aaram se safar.",
  "hi": "प्रीमियम सेवा, पूर्ण गोपनीयता और सहज यात्रा।",
  "bn": "প্রিমিয়াম পরিষেবা, সম্পূর্ণ গোপনীয়তা ও মসৃণ যাত্রা।"
};
NOEL_I18N["home.punctual"] = {
  "en": "Punctual.", "es": "Puntual.", "fr": "Ponctuel.",
  "ar": "دقيق في المواعيد.", "pt": "Pontual.",
  "ur": "Waqt ka paband.", "hi": "समयनिष्ठ।", "bn": "সময়নিষ্ঠ।"
};
NOEL_I18N["home.professional"] = {
  "en": "Professional.", "es": "Profesional.", "fr": "Professionnel.",
  "ar": "محترف.", "pt": "Profissional.",
  "ur": "Professional.", "hi": "पेशेवर।", "bn": "পেশাদার।"
};
NOEL_I18N["home.punctual_p"] = {
  "en": "Our hand-selected chauffeurs prioritise your schedule, route and comfort, ensuring you arrive refreshed for what matters.",
  "es": "Nuestros chóferes seleccionados a mano priorizan tu horario, tu ruta y tu comodidad, para que llegues fresco a lo que importa.",
  "fr": "Nos chauffeurs sélectionnés avec soin privilégient votre emploi du temps, votre itinéraire et votre confort, pour que vous arriviez reposé là où cela compte.",
  "ar": "سائقونا المختارون بعناية يعطون الأولوية لجدولك وطريقك وراحتك، لتصل منتعشًا لما يهمك.",
  "pt": "Nossos motoristas selecionados a dedo priorizam sua agenda, sua rota e seu conforto, para que você chegue descansado ao que importa.",
  "ur": "Hamare haath se chune hue chauffeurs aapke time, route aur aaram ko pehle rakhte hain, taaki aap taaza hoke pahunchen jahan zaroori hai.",
  "hi": "हमारे हाथ से चुने हुए शॉफ़र आपके समय, मार्ग और आराम को प्राथमिकता देते हैं, ताकि आप तरोताज़ा होकर पहुँचें जहाँ ज़रूरी है।",
  "bn": "আমাদের হাতে বাছা শোফাররা আপনার সময়, রুট ও আরামকে অগ্রাধিকার দেন, যাতে আপনি যা গুরুত্বপূর্ণ সেখানে সতেজ হয়ে পৌঁছান।"
};
NOEL_I18N["home.learn_more"] = {
  "en": "Learn more", "es": "Más información", "fr": "En savoir plus",
  "ar": "اعرف المزيد", "pt": "Saiba mais",
  "ur": "Aur janen", "hi": "और जानें", "bn": "আরও জানুন"
};
NOEL_I18N["home.why"] = {
  "en": "Why ride with Noel Chauffer", "es": "Por qué viajar con Noel Chauffer",
  "fr": "Pourquoi voyager avec Noel Chauffer",
  "ar": "لماذا تسافر مع نويل شوفير", "pt": "Por que viajar com a Noel Chauffer",
  "ur": "Noel Chauffer ke saath safar kyun karen", "hi": "नोएल शॉफ़र के साथ यात्रा क्यों करें", "bn": "নোয়েল শোফারের সঙ্গে কেন ভ্রমণ করবেন"
};
NOEL_I18N["home.why_intro"] = {
  "en": "A calm ride starts long before pickup.",
  "es": "Un viaje tranquilo empieza mucho antes de la recogida.",
  "fr": "Un trajet calme commence bien avant la prise en charge.",
  "ar": "الرحلة الهادئة تبدأ قبل الاستلام بوقت طويل.",
  "pt": "Uma viagem tranquila começa muito antes do embarque.",
  "ur": "Aaram wali ride pickup se bahut pehle shuru hoti hai.",
  "hi": "आरामदायक सवारी पिकअप से बहुत पहले शुरू होती है।",
  "bn": "শান্ত রাইড পিকআপের অনেক আগেই শুরু হয়।"
};
NOEL_I18N["home.pro_chauffeurs"] = {
  "en": "Professional chauffeurs", "es": "Chóferes profesionales", "fr": "Chauffeurs professionnels",
  "ar": "سائقون محترفون", "pt": "Motoristas profissionais",
  "ur": "Professional chauffeurs", "hi": "पेशेवर शॉफ़र", "bn": "পেশাদার শোফার"
};
NOEL_I18N["home.pro_chauffeurs_p"] = {
  "en": "Polite, experienced drivers who know the roads and respect your time.",
  "es": "Conductores educados y con experiencia que conocen las carreteras y respetan tu tiempo.",
  "fr": "Des chauffeurs polis et expérimentés qui connaissent les routes et respectent votre temps.",
  "ar": "سائقون مهذبون وذوو خبرة يعرفون الطرق ويحترمون وقتك.",
  "pt": "Motoristas educados e experientes que conhecem as estradas e respeitam seu tempo.",
  "ur": "Shareef aur tajurbekaar drivers jo raaste jaante hain aur aapke time ki qadar karte hain.",
  "hi": "विनम्र, अनुभवी ड्राइवर जो सड़कें जानते हैं और आपके समय का सम्मान करते हैं।",
  "bn": "ভদ্র, অভিজ্ঞ চালক যারা রাস্তা জানেন এবং আপনার সময়কে সম্মান করেন।"
};
NOEL_I18N["home.recent_cars"] = {
  "en": "Recent high-end cars", "es": "Coches recientes de alta gama",
  "fr": "Voitures récentes haut de gamme",
  "ar": "سيارات حديثة فاخرة", "pt": "Carros recentes de alto padrão",
  "ur": "Nayi high-end gaadiyan", "hi": "नई उच्च-स्तरीय गाड़ियाँ", "bn": "নতুন উঁচুমানের গাড়ি"
};
NOEL_I18N["home.recent_cars_p"] = {
  "en": "Clean, comfortable, recent cars, ready for every ride.",
  "es": "Coches limpios, cómodos y recientes, listos para cada viaje.",
  "fr": "Des voitures propres, confortables et récentes, prêtes pour chaque trajet.",
  "ar": "سيارات نظيفة ومريحة وحديثة، جاهزة لكل رحلة.",
  "pt": "Carros limpos, confortáveis e recentes, prontos para cada viagem.",
  "ur": "Saaf, aaramdeh, nayi gaadiyan — har ride ke liye ready.",
  "hi": "साफ़, आरामदायक, नई गाड़ियाँ — हर सवारी के लिए तैयार।",
  "bn": "পরিষ্কার, আরামদায়ক, নতুন গাড়ি — প্রতিটি রাইডের জন্য প্রস্তুত।"
};
NOEL_I18N["home.ontime"] = {
  "en": "On-time pickups", "es": "Recogidas puntuales", "fr": "Prises en charge à l'heure",
  "ar": "استلام في الوقت المحدد", "pt": "Embarques pontuais",
  "ur": "Waqt par pickups", "hi": "समय पर पिकअप", "bn": "সময়মতো পিকআপ"
};
NOEL_I18N["home.ontime_p"] = {
  "en": "Your chauffeur plans the route and arrives on time, every time.",
  "es": "Tu chófer planifica la ruta y llega a tiempo, siempre.",
  "fr": "Votre chauffeur planifie l'itinéraire et arrive à l'heure, à chaque fois.",
  "ar": "سائقك يخطط للطريق ويصل في الوقت المحدد، في كل مرة.",
  "pt": "Seu motorista planeja a rota e chega na hora, sempre.",
  "ur": "Aapka chauffeur route plan karta hai aur har baar waqt par aata hai.",
  "hi": "आपका शॉफ़र रास्ता तय करता है और हर बार समय पर पहुँचता है।",
  "bn": "আপনার শোফার রুট পরিকল্পনা করেন এবং প্রতিবার সময়মতো পৌঁছান।"
};
NOEL_I18N["home.three_ways"] = {
  "en": "Three ways to ride", "es": "Tres formas de viajar", "fr": "Trois façons de voyager",
  "ar": "ثلاث طرق للسفر", "pt": "Três maneiras de viajar",
  "ur": "Safar ke teen tareeqe", "hi": "यात्रा के तीन तरीके", "bn": "ভ্রমণের তিনটি উপায়"
};
NOEL_I18N["home.three_ways_intro"] = {
  "en": "Every booking works the same way: choose your class and pay by card — then your chauffeur is assigned.",
  "es": "Cada reserva funciona igual: elige tu clase y paga con tarjeta; luego se asigna tu chófer.",
  "fr": "Chaque réservation fonctionne de la même façon : choisissez votre classe et payez par carte — votre chauffeur sera ensuite assigné.",
  "ar": "كل حجز يعمل بالطريقة نفسها: اختر فئتك وادفع بالبطاقة — ثم يتم تعيين سائقك.",
  "pt": "Cada reserva funciona da mesma forma: escolha sua classe e pague com cartão — depois seu motorista é designado.",
  "ur": "Har booking ek hi tarah kaam karti hai: apni class chunen aur card se pay karen — phir aapka chauffeur assign ho jayega.",
  "hi": "हर बुकिंग एक ही तरह से काम करती है: अपनी श्रेणी चुनें और कार्ड से भुगतान करें — फिर आपका शॉफ़र नियुक्त हो जाएगा।",
  "bn": "প্রতিটি বুকিং একইভাবে কাজ করে: আপনার শ্রেণি বেছে নিন ও কার্ডে পেমেন্ট করুন — তারপর আপনার শোফার নিয়োগ করা হবে।"
};
NOEL_I18N["home.airport_transfers"] = {
  "en": "Airport Transfers", "es": "Traslados al aeropuerto", "fr": "Transferts aéroport",
  "ar": "النقل من وإلى المطار", "pt": "Transfers de aeroporto",
  "ur": "Airport Transfers", "hi": "एयरपोर्ट ट्रांसफर", "bn": "বিমানবন্দর ট্রান্সফার"
};
NOEL_I18N["home.airport_p"] = {
  "en": "Flying in or out of JFK, LaGuardia, Newark, LAX, ORD or MIA? Your chauffeur meets you at the right terminal. Add your flight number when you book, and take your time — airport pickups include 60 minutes of free waiting.",
  "es": "¿Vuelas desde o hacia JFK, LaGuardia, Newark, LAX, ORD o MIA? Tu chófer te espera en la terminal correcta. Añade tu número de vuelo al reservar y tómate tu tiempo: las recogidas en el aeropuerto incluyen 60 minutos de espera gratis.",
  "fr": "Vous partez ou arrivez à JFK, LaGuardia, Newark, LAX, ORD ou MIA ? Votre chauffeur vous attend au bon terminal. Ajoutez votre numéro de vol lors de la réservation et prenez votre temps — les prises en charge à l'aéroport incluent 60 minutes d'attente gratuite.",
  "ar": "هل تسافر من أو إلى مطارات JFK أو LaGuardia أو Newark أو LAX أو ORD أو MIA؟ سيلقاك سائقك في الصالة الصحيحة. أضف رقم رحلتك عند الحجز وخذ وقتك — يشمل الاستلام من المطار 60 دقيقة انتظار مجاني.",
  "pt": "Voando de ou para JFK, LaGuardia, Newark, LAX, ORD ou MIA? Seu motorista encontrará você no terminal certo. Adicione o número do seu voo ao reservar e não tenha pressa — embarques no aeroporto incluem 60 minutos de espera gratuita.",
  "ur": "JFK, LaGuardia, Newark, LAX, ORD ya MIA se aa rahe hain ya ja rahe hain? Aapka chauffeur sahi terminal par milega. Book karte waqt apni flight number likhen aur aaram se aayen — airport pickups mein 60 minutes free waiting hai.",
  "hi": "JFK, LaGuardia, Newark, LAX, ORD या MIA से आ रहे हैं या जा रहे हैं? आपका शॉफ़र सही टर्मिनल पर मिलेगा। बुक करते समय अपनी फ़्लाइट संख्या जोड़ें और आराम से आएँ — एयरपोर्ट पिकअप में 60 मिनट की मुफ़्त प्रतीक्षा शामिल है।",
  "bn": "JFK, LaGuardia, Newark, LAX, ORD বা MIA থেকে আসছেন বা যাচ্ছেন? আপনার শোফার সঠিক টার্মিনালে দেখা করবেন। বুক করার সময় আপনার ফ্লাইট নম্বর যোগ করুন এবং সময় নিন — বিমানবন্দর পিকআপে ৬০ মিনিট বিনামূল্যে অপেক্ষা অন্তর্ভুক্ত।"
};
NOEL_I18N["home.airport_learn"] = {
  "en": "Learn more about airport transfers", "es": "Más información sobre traslados al aeropuerto",
  "fr": "En savoir plus sur les transferts aéroport",
  "ar": "اعرف المزيد عن النقل من وإلى المطار", "pt": "Saiba mais sobre transfers de aeroporto",
  "ur": "Airport transfers ke baare mein aur janen", "hi": "एयरपोर्ट ट्रांसफर के बारे में और जानें", "bn": "বিমানবন্দর ট্রান্সফার সম্পর্কে আরও জানুন"
};
NOEL_I18N["home.point_to_point"] = {
  "en": "Point to Point", "es": "De puerta a puerta", "fr": "Point à point",
  "ar": "من نقطة إلى نقطة", "pt": "Ponto a ponto",
  "ur": "Point to Point", "hi": "पॉइंट टू पॉइंट", "bn": "পয়েন্ট টু পয়েন্ট"
};
NOEL_I18N["home.point_p"] = {
  "en": "One ride from one address to another, anywhere in the USA. Home to the office, hotel to dinner, or across state lines — your chauffeur takes you straight there, on time.",
  "es": "Un viaje de una dirección a otra, en cualquier lugar de EE. UU. De casa a la oficina, del hotel a la cena o a través de estados: tu chófer te lleva directo, a tiempo.",
  "fr": "Un trajet d'une adresse à une autre, partout aux États-Unis. De la maison au bureau, de l'hôtel au dîner, ou d'un État à l'autre — votre chauffeur vous y conduit directement, à l'heure.",
  "ar": "رحلة واحدة من عنوان إلى آخر، في أي مكان في الولايات المتحدة. من المنزل إلى المكتب، أو من الفندق إلى العشاء، أو عبر حدود الولايات — سائقك يوصلك مباشرة وفي الوقت المحدد.",
  "pt": "Uma viagem de um endereço a outro, em qualquer lugar dos EUA. De casa ao escritório, do hotel ao jantar ou através de estados — seu motorista leva você direto, na hora.",
  "ur": "Ek address se doosre address tak, USA mein kahin bhi. Ghar se office, hotel se dinner, ya state lines ke paar — aapka chauffeur aapko seedha waqt par le jayega.",
  "hi": "एक पते से दूसरे पते तक, अमेरिका में कहीं भी। घर से दफ़्तर, होटल से डिनर, या राज्य की सीमा पार — आपका शॉफ़र आपको सीधे समय पर ले जाएगा।",
  "bn": "এক ঠিকানা থেকে অন্য ঠিকানায়, যুক্তরাষ্ট্রের যেকোনো জায়গায়। বাড়ি থেকে অফিস, হোটেল থেকে ডিনার, বা রাজ্যের সীমানা পেরিয়ে — আপনার শোফার আপনাকে সোজা সময়মতো নিয়ে যাবেন।"
};
NOEL_I18N["home.point_learn"] = {
  "en": "Learn more about point-to-point rides", "es": "Más información sobre viajes de puerta a puerta",
  "fr": "En savoir plus sur les trajets point à point",
  "ar": "اعرف المزيد عن الرحلات من نقطة إلى نقطة", "pt": "Saiba mais sobre viagens ponto a ponto",
  "ur": "Point-to-point rides ke baare mein aur janen", "hi": "पॉइंट टू पॉइंट सवारी के बारे में और जानें", "bn": "পয়েন্ট টু পয়েন্ট রাইড সম্পর্কে আরও জানুন"
};
NOEL_I18N["home.hourly"] = {
  "en": "Hourly as Directed", "es": "Por horas, a tu disposición", "fr": "À l'heure, à votre disposition",
  "ar": "بالساعة حسب توجيهك", "pt": "Por hora, à sua disposição",
  "ur": "Hourly as Directed", "hi": "निर्देशानुसार घंटे के हिसाब से", "bn": "নির্দেশমতো ঘণ্টা হিসেবে"
};
NOEL_I18N["home.hourly_p"] = {
  "en": "Keep your chauffeur for as long as you need. Several stops, meetings across town, or a whole evening out — book by the hour.",
  "es": "Quédate con tu chófer todo el tiempo que necesites. Varias paradas, reuniones por la ciudad o toda una noche fuera: reserva por horas.",
  "fr": "Gardez votre chauffeur aussi longtemps que nécessaire. Plusieurs arrêts, des réunions en ville ou une soirée entière — réservez à l'heure.",
  "ar": "احتفظ بسائقك طالما احتجت. عدة توقفات أو اجتماعات عبر المدينة أو أمسية كاملة — احجز بالساعة.",
  "pt": "Fique com seu motorista pelo tempo que precisar. Várias paradas, reuniões pela cidade ou uma noite inteira — reserve por hora.",
  "ur": "Apne chauffeur ko jitni der chahiye utni der rakhen. Kai stops, sheher bhar mein meetings, ya poori shaam — hour ke hisaab se book karen.",
  "hi": "अपने शॉफ़र को जितनी देर चाहें उतनी देर रखें। कई रुकावटें, शहर भर में बैठकें, या पूरी शाम — घंटे के हिसाब से बुक करें।",
  "bn": "যতক্ষণ দরকার আপনার শোফারকে রাখুন। একাধিক স্টপ, শহরজুড়ে মিটিং, বা পুরো সন্ধ্যা — ঘণ্টা হিসেবে বুক করুন।"
};
NOEL_I18N["home.hourly_learn"] = {
  "en": "Learn more about hourly hire", "es": "Más información sobre alquiler por horas",
  "fr": "En savoir plus sur la location à l'heure",
  "ar": "اعرف المزيد عن الحجز بالساعة", "pt": "Saiba mais sobre aluguel por hora",
  "ur": "Hourly hire ke baare mein aur janen", "hi": "घंटे के हिसाब से किराए के बारे में और जानें", "bn": "ঘণ্টা হিসেবে ভাড়া সম্পর্কে আরও জানুন"
};
NOEL_I18N["home.move"] = {
  "en": "We move with you", "es": "Nos movemos contigo", "fr": "Nous bougeons avec vous",
  "ar": "نتنقل معك", "pt": "Nós nos movemos com você",
  "ur": "Hum aapke saath chalte hain", "hi": "हम आपके साथ चलते हैं", "bn": "আমরা আপনার সঙ্গে চলি"
};
NOEL_I18N["home.gold"] = {
  "en": "The gold standard of private travel.", "es": "El estándar de oro del viaje privado.",
  "fr": "La référence du voyage privé.",
  "ar": "المعيار الذهبي للسفر الخاص.", "pt": "O padrão ouro da viagem privada.",
  "ur": "Private travel ka gold standard.", "hi": "निजी यात्रा का स्वर्ण मानक।", "bn": "ব্যক্তিগত ভ্রমণের স্বর্ণমান।"
};
NOEL_I18N["home.gold_intro"] = {
  "en": "Our hand-selected chauffeurs prioritise your schedule, route, and comfort, ensuring you arrive refreshed for what matters.",
  "es": "Nuestros chóferes seleccionados a mano priorizan tu horario, tu ruta y tu comodidad, para que llegues fresco a lo que importa.",
  "fr": "Nos chauffeurs sélectionnés avec soin privilégient votre emploi du temps, votre itinéraire et votre confort, pour que vous arriviez reposé là où cela compte.",
  "ar": "سائقونا المختارون بعناية يعطون الأولوية لجدولك وطريقك وراحتك، لتصل منتعشًا لما يهمك.",
  "pt": "Nossos motoristas selecionados a dedo priorizam sua agenda, sua rota e seu conforto, para que você chegue descansado ao que importa.",
  "ur": "Hamare haath se chune hue chauffeurs aapke time, route aur aaram ko pehle rakhte hain, taaki aap taaza hoke pahunchen jahan zaroori hai.",
  "hi": "हमारे हाथ से चुने हुए शॉफ़र आपके समय, मार्ग और आराम को प्राथमिकता देते हैं, ताकि आप तरोताज़ा होकर पहुँचें जहाँ ज़रूरी है।",
  "bn": "আমাদের হাতে বাছা শোফাররা আপনার সময়, রুট ও আরামকে অগ্রাধিকার দেন, যাতে আপনি যা গুরুত্বপূর্ণ সেখানে সতেজ হয়ে পৌঁছান।"
};
NOEL_I18N["home.available"] = {
  "en": "Available 24/7", "es": "Disponible 24/7", "fr": "Disponible 24 h/24, 7 j/7",
  "ar": "متاح على مدار الساعة", "pt": "Disponível 24/7",
  "ur": "24/7 available", "hi": "24/7 उपलब्ध", "bn": "২৪/৭ উপলব্ধ"
};
NOEL_I18N["home.available_p"] = {
  "en": "Book anytime, anywhere.", "es": "Reserva cuando quieras, donde quieras.",
  "fr": "Réservez à tout moment, partout.",
  "ar": "احجز في أي وقت ومن أي مكان.", "pt": "Reserve a qualquer hora, em qualquer lugar.",
  "ur": "Kabhi bhi, kahin se bhi book karen.", "hi": "कभी भी, कहीं से भी बुक करें।", "bn": "যেকোনো সময়, যেকোনো জায়গা থেকে বুক করুন।"
};
NOEL_I18N["home.flight_number"] = {
  "en": "Flight number", "es": "Número de vuelo", "fr": "Numéro de vol",
  "ar": "رقم الرحلة", "pt": "Número do voo",
  "ur": "Flight number", "hi": "फ़्लाइट नंबर", "bn": "ফ্লাইট নম্বর"
};
NOEL_I18N["home.flight_p"] = {
  "en": "We adjust to your schedule.", "es": "Nos adaptamos a tu horario.",
  "fr": "Nous nous adaptons à votre emploi du temps.",
  "ar": "نتكيف مع جدولك.", "pt": "Nos adaptamos à sua agenda.",
  "ur": "Hum aapke schedule ke hisaab se adjust karte hain.",
  "hi": "हम आपके कार्यक्रम के अनुसार ढल जाते हैं।",
  "bn": "আমরা আপনার সময়সূচি অনুযায়ী মানিয়ে নিই।"
};
NOEL_I18N["home.fleet"] = {
  "en": "Diverse Fleet", "es": "Flota variada", "fr": "Flotte variée",
  "ar": "أسطول متنوع", "pt": "Frota diversificada",
  "ur": "Diverse Fleet", "hi": "विविध बेड़ा", "bn": "বৈচিত্র্যময় বহর"
};
NOEL_I18N["home.fleet_p"] = {
  "en": "From executive sedans to spacious SUVs.",
  "es": "Desde berlinas ejecutivas hasta SUV espaciosos.",
  "fr": "Des berlines exécutives aux SUV spacieux.",
  "ar": "من سيارات السيدان التنفيذية إلى سيارات الدفع الرباعي الواسعة.",
  "pt": "De sedãs executivos a SUVs espaçosos.",
  "ur": "Executive sedans se le kar spacious SUVs tak.",
  "hi": "एग्ज़ीक्यूटिव सेडान से लेकर विशाल SUV तक।",
  "bn": "এক্সিকিউটিভ সেডান থেকে প্রশস্ত SUV পর্যন্ত।"
};

/* ---- Footer / bottom ---- */
NOEL_I18N["foot.tagline"] = {
  "en": "Luxury Chauffeur Rides Across USA — premium chauffeur service, on-time pickups, clear communication.",
  "es": "Viajes de lujo con chófer en todo EE. UU.: servicio premium, recogidas puntuales y comunicación clara.",
  "fr": "Trajets de luxe avec chauffeur partout aux États-Unis — service premium, prises en charge à l'heure et communication claire.",
  "ar": "رحلات فاخرة مع سائق في جميع أنحاء الولايات المتحدة — خدمة مميزة واستلام في الوقت المحدد وتواصل واضح.",
  "pt": "Viagens de luxo com motorista em todos os EUA — serviço premium, embarques pontuais e comunicação clara.",
  "ur": "USA bhar mein luxury chauffeur rides — premium service, waqt par pickups, saaf communication.",
  "hi": "पूरे अमेरिका में लग्ज़री शॉफ़र सवारी — प्रीमियम सेवा, समय पर पिकअप, स्पष्ट संवाद।",
  "bn": "সারা যুক্তরাষ্ট্রজুড়ে বিলাসবহুল শোফার রাইড — প্রিমিয়াম পরিষেবা, সময়মতো পিকআপ, পরিষ্কার যোগাযোগ।"
};
NOEL_I18N["foot.hourly"] = {
  "en": "Hourly", "es": "Por horas", "fr": "À l'heure",
  "ar": "بالساعة", "pt": "Por hora",
  "ur": "Hourly", "hi": "घंटे के हिसाब से", "bn": "ঘণ্টা হিসেবে"
};
NOEL_I18N["foot.corporate"] = {
  "en": "Corporate", "es": "Corporativo", "fr": "Entreprises",
  "ar": "للشركات", "pt": "Corporativo",
  "ur": "Corporate", "hi": "कॉर्पोरेट", "bn": "কর্পোরেট"
};
NOEL_I18N["foot.wedding"] = {
  "en": "Wedding", "es": "Bodas", "fr": "Mariage",
  "ar": "زفاف", "pt": "Casamento",
  "ur": "Wedding", "hi": "विवाह", "bn": "বিয়ে"
};
NOEL_I18N["foot.jfk_transfers"] = {
  "en": "JFK Airport Transfers", "es": "Traslados al aeropuerto JFK", "fr": "Transferts aéroport JFK",
  "ar": "النقل من وإلى مطار JFK", "pt": "Transfers do aeroporto JFK",
  "ur": "JFK Airport Transfers", "hi": "JFK एयरपोर्ट ट्रांसफर", "bn": "JFK বিমানবন্দর ট্রান্সফার"
};
NOEL_I18N["foot.lga_transfers"] = {
  "en": "LaGuardia Airport Transfers", "es": "Traslados al aeropuerto LaGuardia", "fr": "Transferts aéroport LaGuardia",
  "ar": "النقل من وإلى مطار LaGuardia", "pt": "Transfers do aeroporto LaGuardia",
  "ur": "LaGuardia Airport Transfers", "hi": "LaGuardia एयरपोर्ट ट्रांसफर", "bn": "LaGuardia বিমানবন্দর ট্রান্সফার"
};
NOEL_I18N["foot.ewr_transfers"] = {
  "en": "Newark Airport Transfers", "es": "Traslados al aeropuerto Newark", "fr": "Transferts aéroport Newark",
  "ar": "النقل من وإلى مطار Newark", "pt": "Transfers do aeroporto Newark",
  "ur": "Newark Airport Transfers", "hi": "Newark एयरपोर्ट ट्रांसफर", "bn": "Newark বিমানবন্দর ট্রান্সফার"
};
NOEL_I18N["foot.teb_transfers"] = {
  "en": "Teterboro Airport Transfers", "es": "Traslados al aeropuerto Teterboro", "fr": "Transferts aéroport Teterboro",
  "ar": "النقل من وإلى مطار Teterboro", "pt": "Transfers do aeroporto Teterboro",
  "ur": "Teterboro Airport Transfers", "hi": "Teterboro एयरपोर्ट ट्रांसफर", "bn": "Teterboro বিমানবন্দর ট্রান্সফার"
};
NOEL_I18N["foot.guide_jfk_vs"] = {
  "en": "JFK vs LaGuardia vs Newark", "es": "JFK frente a LaGuardia frente a Newark", "fr": "JFK vs LaGuardia vs Newark",
  "ar": "JFK مقابل LaGuardia مقابل Newark", "pt": "JFK vs LaGuardia vs Newark",
  "ur": "JFK vs LaGuardia vs Newark", "hi": "JFK बनाम LaGuardia बनाम Newark", "bn": "JFK বনাম LaGuardia বনাম Newark"
};
NOEL_I18N["foot.guide_blackcar"] = {
  "en": "Black car vs Uber Black", "es": "Coche negro frente a Uber Black", "fr": "Voiture noire vs Uber Black",
  "ar": "السيارة السوداء مقابل Uber Black", "pt": "Carro preto vs Uber Black",
  "ur": "Black car vs Uber Black", "hi": "ब्लैक कार बनाम Uber Black", "bn": "ব্ল্যাক কার বনাম Uber Black"
};
NOEL_I18N["foot.guide_jfk_terminal"] = {
  "en": "JFK terminal pickup guide", "es": "Guía de recogida en la terminal de JFK", "fr": "Guide de prise en charge au terminal JFK",
  "ar": "دليل الاستلام من صالة JFK", "pt": "Guia de embarque no terminal JFK",
  "ur": "JFK terminal pickup guide", "hi": "JFK टर्मिनल पिकअप गाइड", "bn": "JFK টার্মিনাল পিকআপ গাইড"
};
NOEL_I18N["foot.guide_how_much"] = {
  "en": "How much is a black car in NYC?", "es": "¿Cuánto cuesta un coche negro en Nueva York?", "fr": "Combien coûte une voiture noire à New York ?",
  "ar": "كم تكلفة السيارة السوداء في نيويورك؟", "pt": "Quanto custa um carro preto em Nova York?",
  "ur": "NYC mein black car kitne ki hai?", "hi": "NYC में ब्लैक कार कितने की है?", "bn": "NYC-তে ব্ল্যাক কার কত?"
};
NOEL_I18N["foot.all_guides"] = {
  "en": "All guides", "es": "Todas las guías", "fr": "Tous les guides",
  "ar": "كل الأدلة", "pt": "Todos os guias",
  "ur": "Saare guides", "hi": "सभी गाइड", "bn": "সব গাইড"
};
NOEL_I18N["foot.about"] = {
  "en": "Premium chauffeur service across the USA. On-time pickups, calm and comfortable rides.",
  "es": "Servicio premium de chófer en todo EE. UU. Recogidas puntuales, viajes tranquilos y cómodos.",
  "fr": "Service de chauffeur premium partout aux États-Unis. Prises en charge à l'heure, trajets calmes et confortables.",
  "ar": "خدمة سائق مميزة في جميع أنحاء الولايات المتحدة. استلام في الوقت المحدد ورحلات هادئة ومريحة.",
  "pt": "Serviço premium de motorista em todos os EUA. Embarques pontuais, viagens calmas e confortáveis.",
  "ur": "USA bhar mein premium chauffeur service. Waqt par pickups, aaramdeh aur sakoon wali rides.",
  "hi": "पूरे अमेरिका में प्रीमियम शॉफ़र सेवा। समय पर पिकअप, शांत और आरामदायक सवारी।",
  "bn": "সারা যুক্তরাষ্ট্রজুড়ে প্রিমিয়াম শোফার পরিষেবা। সময়মতো পিকআপ, শান্ত ও আরামদায়ক রাইড।"
};
NOEL_I18N["foot.airport_transfers"] = {
  "en": "Airport transfers", "es": "Traslados al aeropuerto", "fr": "Transferts aéroport",
  "ar": "النقل من وإلى المطار", "pt": "Transfers de aeroporto",
  "ur": "Airport transfers", "hi": "एयरपोर्ट ट्रांसफर", "bn": "বিমানবন্দর ট্রান্সফার"
};
NOEL_I18N["foot.where"] = {
  "en": "Where we drive", "es": "Dónde conducimos", "fr": "Où nous conduisons",
  "ar": "أين نقود", "pt": "Onde dirigimos",
  "ur": "Hum kahan drive karte hain", "hi": "हम कहाँ ड्राइव करते हैं", "bn": "আমরা কোথায় গাড়ি চালাই"
};
NOEL_I18N["foot.guides"] = {
  "en": "Guides", "es": "Guías", "fr": "Guides",
  "ar": "أدلة", "pt": "Guias",
  "ur": "Guides", "hi": "गाइड", "bn": "গাইড"
};
NOEL_I18N["foot.services"] = {
  "en": "Services", "es": "Servicios", "fr": "Services",
  "ar": "الخدمات", "pt": "Serviços",
  "ur": "Services", "hi": "सेवाएँ", "bn": "পরিষেবা"
};
NOEL_I18N["foot.company"] = {
  "en": "Company", "es": "Empresa", "fr": "Entreprise",
  "ar": "الشركة", "pt": "Empresa",
  "ur": "Company", "hi": "कंपनी", "bn": "কোম্পানি"
};
NOEL_I18N["foot.drive_with_us"] = {
  "en": "Drive with us", "es": "Conduce con nosotros", "fr": "Conduisez avec nous",
  "ar": "قُد معنا", "pt": "Dirija conosco",
  "ur": "Hamare saath drive karen", "hi": "हमारे साथ ड्राइव करें", "bn": "আমাদের সঙ্গে গাড়ি চালান"
};
NOEL_I18N["foot.app"] = {
  "en": "App", "es": "App", "fr": "App",
  "ar": "التطبيق", "pt": "App",
  "ur": "App", "hi": "ऐप", "bn": "অ্যাপ"
};
NOEL_I18N["foot.privacy"] = {
  "en": "Privacy Policy", "es": "Política de privacidad", "fr": "Politique de confidentialité",
  "ar": "سياسة الخصوصية", "pt": "Política de Privacidade",
  "ur": "Privacy Policy", "hi": "गोपनीयता नीति", "bn": "গোপনীয়তা নীতি"
};
NOEL_I18N["foot.terms"] = {
  "en": "Terms", "es": "Términos", "fr": "Conditions",
  "ar": "الشروط", "pt": "Termos",
  "ur": "Terms", "hi": "शर्तें", "bn": "শর্তাবলী"
};
NOEL_I18N["foot.hourly_hire"] = {
  "en": "Hourly hire", "es": "Alquiler por horas", "fr": "Location à l'heure",
  "ar": "الحجز بالساعة", "pt": "Aluguel por hora",
  "ur": "Hourly hire", "hi": "घंटे के हिसाब से किराया", "bn": "ঘণ্টা হিসেবে ভাড়া"
};
NOEL_I18N["foot.corporate_travel"] = {
  "en": "Corporate travel", "es": "Viajes corporativos", "fr": "Voyages d'affaires",
  "ar": "سفر الشركات", "pt": "Viagens corporativas",
  "ur": "Corporate travel", "hi": "कॉर्पोरेट यात्रा", "bn": "কর্পোরেট ভ্রমণ"
};
NOEL_I18N["foot.wedding_chauffeur"] = {
  "en": "Wedding chauffeur", "es": "Chófer para bodas", "fr": "Chauffeur de mariage",
  "ar": "سائق الزفاف", "pt": "Motorista de casamento",
  "ur": "Wedding chauffeur", "hi": "विवाह शॉफ़र", "bn": "বিয়ের শোফার"
};
NOEL_I18N["foot.point_to_point"] = {
  "en": "Point to point", "es": "De puerta a puerta", "fr": "Point à point",
  "ar": "من نقطة إلى نقطة", "pt": "Ponto a ponto",
  "ur": "Point to point", "hi": "पॉइंट टू पॉइंट", "bn": "পয়েন্ট টু পয়েন্ট"
};
NOEL_I18N["foot.reserved"] = {
  "en": "All rights reserved.", "es": "Todos los derechos reservados.", "fr": "Tous droits réservés.",
  "ar": "جميع الحقوق محفوظة.", "pt": "Todos os direitos reservados.",
  "ur": "All rights reserved.", "hi": "सर्वाधिकार सुरक्षित।", "bn": "সর্বস্বত্ব সংরক্ষিত।"
};
NOEL_I18N["foot.powered_by"] = {
  "en": "Powered by Noel Chauffer", "es": "Con la tecnología de Noel Chauffer",
  "fr": "Propulsé par Noel Chauffer",
  "ar": "مدعوم من نويل شوفير", "pt": "Desenvolvido por Noel Chauffer",
  "ur": "Powered by Noel Chauffer", "hi": "नोएल शॉफ़र द्वारा संचालित", "bn": "নোয়েল শোফার দ্বারা চালিত"
};

/* ---- Customer app tabs / headings ---- */
NOEL_I18N["app.book"] = {
  "en": "Book", "es": "Reservar", "fr": "Réserver",
  "ar": "احجز", "pt": "Reservar",
  "ur": "Book karen", "hi": "बुक करें", "bn": "বুক করুন"
};
NOEL_I18N["app.tag"] = {
  "en": "Luxury Chauffeur Rides Across USA", "es": "Viajes de lujo con chófer en todo EE. UU.",
  "fr": "Trajets de luxe avec chauffeur partout aux États-Unis",
  "ar": "رحلات فاخرة مع سائق في جميع أنحاء الولايات المتحدة", "pt": "Viagens de luxo com motorista em todos os EUA",
  "ur": "USA bhar mein luxury chauffeur rides", "hi": "पूरे अमेरिका में लग्ज़री शॉफ़र सवारी", "bn": "সারা যুক্তরাষ্ট্রজুড়ে বিলাসবহুল শোফার রাইড"
};
NOEL_I18N["app.my_rides_heading"] = {
  "en": "My rides", "es": "Mis viajes", "fr": "Mes trajets",
  "ar": "رحلاتي", "pt": "Minhas viagens",
  "ur": "Meri rides", "hi": "मेरी सवारियाँ", "bn": "আমার রাইডগুলো"
};
NOEL_I18N["app.history_intro"] = {
  "en": "Enter the phone number you booked with to see your rides.",
  "es": "Escribe el número de teléfono con el que reservaste para ver tus viajes.",
  "fr": "Saisissez le numéro de téléphone utilisé pour réserver afin de voir vos trajets.",
  "ar": "أدخل رقم الهاتف الذي حجزت به لترى رحلاتك.",
  "pt": "Informe o número de telefone usado na reserva para ver suas viagens.",
  "ur": "Apni rides dekhne ke liye wo phone number likhen jis se book kiya tha.",
  "hi": "अपनी सवारियाँ देखने के लिए वह फ़ोन नंबर लिखें जिससे आपने बुक किया था।",
  "bn": "আপনার রাইড দেখতে যে ফোন নম্বর দিয়ে বুক করেছিলেন তা লিখুন।"
};
NOEL_I18N["app.signed_in_as"] = {
  "en": "Signed in as", "es": "Sesión iniciada como", "fr": "Connecté en tant que",
  "ar": "تم تسجيل الدخول باسم", "pt": "Conectado como",
  "ur": "Signed in as", "hi": "इस रूप में साइन इन किया गया", "bn": "হিসেবে সাইন ইন করা হয়েছে"
};
NOEL_I18N["app.showing_rides"] = {
  "en": "— showing your rides.", "es": "— mostrando tus viajes.", "fr": "— affichage de vos trajets.",
  "ar": "— عرض رحلاتك.", "pt": "— mostrando suas viagens.",
  "ur": "— aapki rides dikhayi ja rahi hain.", "hi": "— आपकी सवारियाँ दिखाई जा रही हैं।", "bn": "— আপনার রাইড দেখানো হচ্ছে।"
};
NOEL_I18N["app.history_phone_ph"] = {
  "en": "Phone number used for booking", "es": "Número de teléfono usado para reservar",
  "fr": "Numéro de téléphone utilisé pour la réservation",
  "ar": "رقم الهاتف المستخدم للحجز", "pt": "Número de telefone usado na reserva",
  "ur": "Booking ke liye use kiya gaya phone number", "hi": "बुकिंग के लिए इस्तेमाल किया गया फ़ोन नंबर", "bn": "বুকিংয়ের জন্য ব্যবহৃত ফোন নম্বর"
};
NOEL_I18N["app.show_rides"] = {
  "en": "Show my rides", "es": "Mostrar mis viajes", "fr": "Afficher mes trajets",
  "ar": "اعرض رحلاتي", "pt": "Mostrar minhas viagens",
  "ur": "Meri rides dikhayen", "hi": "मेरी सवारियाँ दिखाएँ", "bn": "আমার রাইড দেখান"
};
NOEL_I18N["app.all_rides"] = {
  "en": "← All rides", "es": "← Todos los viajes", "fr": "← Tous les trajets",
  "ar": "← كل الرحلات", "pt": "← Todas as viagens",
  "ur": "← Saari rides", "hi": "← सभी सवारियाँ", "bn": "← সব রাইড"
};
NOEL_I18N["app.support_intro"] = {
  "en": "We reply within 24 hours. Ask about booking, cancellation, waiting time, or a ride you have already booked.",
  "es": "Respondemos en un plazo de 24 horas. Pregunta sobre reservas, cancelación, tiempo de espera o un viaje que ya reservaste.",
  "fr": "Nous répondons sous 24 heures. Posez vos questions sur la réservation, l'annulation, le temps d'attente ou un trajet déjà réservé.",
  "ar": "نرد خلال 24 ساعة. اسأل عن الحجز أو الإلغاء أو وقت الانتظار أو رحلة حجزتها بالفعل.",
  "pt": "Respondemos em até 24 horas. Pergunte sobre reserva, cancelamento, tempo de espera ou uma viagem já reservada.",
  "ur": "Hum 24 hours ke andar reply karte hain. Booking, cancellation, waiting time, ya pehle se book ki hui ride ke baare mein poochhen.",
  "hi": "हम 24 घंटों के भीतर जवाब देते हैं। बुकिंग, रद्दीकरण, प्रतीक्षा समय, या पहले से बुक की गई सवारी के बारे में पूछें।",
  "bn": "আমরা ২৪ ঘণ্টার মধ্যে উত্তর দিই। বুকিং, বাতিল, অপেক্ষার সময়, বা ইতিমধ্যে বুক করা রাইড সম্পর্কে জিজ্ঞেস করুন।"
};
NOEL_I18N["app.email_us"] = {
  "en": "You can also email us at", "es": "También puedes escribirnos a", "fr": "Vous pouvez aussi nous écrire à",
  "ar": "يمكنك أيضًا مراسلتنا على", "pt": "Você também pode nos enviar um e-mail para",
  "ur": "Aap hamein email bhi kar sakte hain:", "hi": "आप हमें इस पर भी ईमेल कर सकते हैं", "bn": "আপনি আমাদের ইমেইলও করতে পারেন"
};
NOEL_I18N["foot.phone_label"] = {
  "en": "Phone:", "es": "Teléfono:", "fr": "Téléphone :",
  "ar": "الهاتف:", "pt": "Telefone:",
  "ur": "Phone:", "hi": "फ़ोन:", "bn": "ফোন:"
};
NOEL_I18N["foot.email_label"] = {
  "en": "Email:", "es": "Correo:", "fr": "E-mail :",
  "ar": "البريد الإلكتروني:", "pt": "E-mail:",
  "ur": "Email:", "hi": "ईमेल:", "bn": "ইমেইল:"
};
NOEL_I18N["form.flight_text"] = {
  "en": "Your chauffeur will meet you at the right terminal.",
  "es": "Tu chófer te recibirá en la terminal correcta.",
  "fr": "Votre chauffeur vous accueillera au bon terminal.",
  "ar": "سيستقبلك سائقك في الصالة الصحيحة.",
  "pt": "Seu motorista irá encontrá-lo no terminal correto.",
  "ur": "Aapka chauffeur aapko sahi terminal par milega.",
  "hi": "आपका चालक आपको सही टर्मिनल पर मिलेगा।",
  "bn": "আপনার চালক আপনাকে সঠিক টার্মিনালে স্বাগত জানাবেন।"
};
NOEL_I18N["form.ride_type"] = {
  "en": "Ride type", "es": "Tipo de viaje", "fr": "Type de trajet",
  "ar": "نوع الرحلة", "pt": "Tipo de viagem",
  "ur": "Ride type", "hi": "सवारी का प्रकार", "bn": "রাইডের ধরন"
};
NOEL_I18N["form.by_hour"] = {
  "en": "By the hour", "es": "Por horas", "fr": "À l'heure",
  "ar": "بالساعة", "pt": "Por hora",
  "ur": "By the hour", "hi": "प्रति घंटा", "bn": "ঘণ্টা অনুযায়ী"
};
NOEL_I18N["form.flight_ph2"] = {
  "en": "e.g. EK215", "es": "p. ej., EK215", "fr": "p. ex. EK215",
  "ar": "مثال: EK215", "pt": "ex.: EK215",
  "ur": "masalan EK215", "hi": "जैसे EK215", "bn": "যেমন EK215"
};
NOEL_I18N["status.plate_label"] = {
  "en": "Plate:", "es": "Matrícula:", "fr": "Plaque :",
  "ar": "اللوحة:", "pt": "Placa:",
  "ur": "Plate:", "hi": "प्लेट:", "bn": "প্লেট:"
};
NOEL_I18N["class.prev_highlight"] = {
  "en": "Previous highlight", "es": "Aspecto anterior", "fr": "Point fort précédent",
  "ar": "الميزة السابقة", "pt": "Destaque anterior",
  "ur": "Pichli highlight", "hi": "पिछली विशेषता", "bn": "আগের হাইলাইট"
};
NOEL_I18N["class.next_highlight"] = {
  "en": "Next highlight", "es": "Siguiente aspecto", "fr": "Point fort suivant",
  "ar": "الميزة التالية", "pt": "Próximo destaque",
  "ur": "Agli highlight", "hi": "अगली विशेषता", "bn": "পরের হাইলাইট"
};
NOEL_I18N["class.highlights"] = {
  "en": "Highlights", "es": "Aspectos destacados", "fr": "Points forts",
  "ar": "المزايا", "pt": "Destaques",
  "ur": "Highlights", "hi": "मुख्य बातें", "bn": "হাইলাইট"
};
NOEL_I18N["menu.app_link"] = {
  "en": "App", "es": "App", "fr": "Appli",
  "ar": "التطبيق", "pt": "App",
  "ur": "App", "hi": "ऐप", "bn": "অ্যাপ"
};
NOEL_I18N["menu.drive_with_us"] = {
  "en": "Drive with us", "es": "Conduce con nosotros", "fr": "Conduisez avec nous",
  "ar": "قُد معنا", "pt": "Dirija conosco",
  "ur": "Hamare saath drive karen", "hi": "हमारे साथ चलाएँ", "bn": "আমাদের সাথে ড্রাইভ করুন"
};
NOEL_I18N["app.book_ride"] = {
  "en": "Book your ride", "es": "Reserva tu viaje", "fr": "Réservez votre trajet",
  "ar": "احجز رحلتك", "pt": "Reserve sua viagem",
  "ur": "Apni ride book karen", "hi": "अपनी सवारी बुक करें", "bn": "আপনার রাইড বুক করুন"
};
NOEL_I18N["app.home"] = {
  "en": "Home", "es": "Inicio", "fr": "Accueil",
  "ar": "الرئيسية", "pt": "Início",
  "ur": "Home", "hi": "होम", "bn": "হোম"
};
NOEL_I18N["app.history_intro_past"] = {
  "en": "Enter the phone number you booked with to see your past rides.",
  "es": "Escribe el número de teléfono con el que reservaste para ver tus viajes pasados.",
  "fr": "Saisissez le numéro de téléphone utilisé pour réserver afin de voir vos trajets passés.",
  "ar": "أدخل رقم الهاتف الذي حجزت به لترى رحلاتك السابقة.",
  "pt": "Informe o número de telefone usado na reserva para ver suas viagens anteriores.",
  "ur": "Apni pichli rides dekhne ke liye wo phone number likhen jis se book kiya tha.",
  "hi": "अपनी पिछली सवारियाँ देखने के लिए वह फ़ोन नंबर लिखें जिससे आपने बुक किया था।",
  "bn": "আপনার আগের রাইড দেখতে যে ফোন নম্বর দিয়ে বুক করেছিলেন তা লিখুন।"
};
NOEL_I18N["status.looking_up"] = {
  "en": "Looking up your rides…", "es": "Buscando tus viajes…", "fr": "Recherche de vos trajets…",
  "ar": "جارٍ البحث عن رحلاتك…", "pt": "Procurando suas viagens…",
  "ur": "Aapki rides dhoondhi ja rahi hain…", "hi": "आपकी सवारियाँ खोजी जा रही हैं…", "bn": "আপনার রাইড খোঁজা হচ্ছে…"
};
NOEL_I18N["status.no_rides_email"] = {
  "en": "No rides found for this email yet.", "es": "Aún no hay viajes para este correo.",
  "fr": "Aucun trajet trouvé pour cet e-mail pour le moment.",
  "ar": "لم يتم العثور على رحلات لهذا البريد الإلكتروني بعد.", "pt": "Nenhuma viagem encontrada para este e-mail ainda.",
  "ur": "Is email ke liye abhi koi rides nahi mili.", "hi": "इस ईमेल के लिए अभी कोई सवारी नहीं मिली।", "bn": "এই ইমেইলের জন্য এখনো কোনো রাইড পাওয়া যায়নি।"
};
NOEL_I18N["status.no_rides_number"] = {
  "en": "No rides found for that number yet.", "es": "Aún no hay viajes para ese número.",
  "fr": "Aucun trajet trouvé pour ce numéro pour le moment.",
  "ar": "لم يتم العثور على رحلات لهذا الرقم بعد.", "pt": "Nenhuma viagem encontrada para esse número ainda.",
  "ur": "Is number ke liye abhi koi rides nahi mili.", "hi": "इस नंबर के लिए अभी कोई सवारी नहीं मिली।", "bn": "এই নম্বরের জন্য এখনো কোনো রাইড পাওয়া যায়নি।"
};
NOEL_I18N["status.enter_phone"] = {
  "en": "Please enter your phone number.", "es": "Escribe tu número de teléfono.",
  "fr": "Veuillez saisir votre numéro de téléphone.",
  "ar": "يرجى إدخال رقم هاتفك.", "pt": "Informe seu número de telefone.",
  "ur": "Apna phone number likhen.", "hi": "कृपया अपना फ़ोन नंबर लिखें।", "bn": "আপনার ফোন নম্বর লিখুন।"
};
NOEL_I18N["status.lookup_failed"] = {
  "en": "Could not look up rides for that number.", "es": "No se pudieron buscar viajes para ese número.",
  "fr": "Impossible de rechercher des trajets pour ce numéro.",
  "ar": "تعذّر البحث عن رحلات لهذا الرقم.", "pt": "Não foi possível buscar viagens para esse número.",
  "ur": "Is number ke liye rides nahi mil saki.", "hi": "उस नंबर के लिए सवारियाँ नहीं मिल सकीं।", "bn": "ওই নম্বরের জন্য রাইড খুঁজে পাওয়া যায়নি।"
};
NOEL_I18N["app.my_rides"] = {
  "en": "My Rides", "es": "Mis viajes", "fr": "Mes trajets",
  "ar": "رحلاتي", "pt": "Minhas viagens",
  "ur": "Meri Rides", "hi": "मेरी सवारियाँ", "bn": "আমার রাইডগুলো"
};
NOEL_I18N["app.support"] = {
  "en": "Support", "es": "Ayuda", "fr": "Assistance",
  "ar": "الدعم", "pt": "Suporte",
  "ur": "Support", "hi": "सहायता", "bn": "সহায়তা"
};
NOEL_I18N["app.book_your_ride"] = {
  "en": "Book your ride", "es": "Reserva tu viaje", "fr": "Réservez votre trajet",
  "ar": "احجز رحلتك", "pt": "Reserve sua viagem",
  "ur": "Apni ride book karen", "hi": "अपनी सवारी बुक करें", "bn": "আপনার রাইড বুক করুন"
};
NOEL_I18N["app.your_rides"] = {
  "en": "Your rides", "es": "Tus viajes", "fr": "Vos trajets",
  "ar": "رحلاتك", "pt": "Suas viagens",
  "ur": "Aapki rides", "hi": "आपकी सवारियाँ", "bn": "আপনার রাইডগুলো"
};
NOEL_I18N["app.book_another"] = {
  "en": "Book another ride", "es": "Reservar otro viaje", "fr": "Réserver un autre trajet",
  "ar": "احجز رحلة أخرى", "pt": "Reservar outra viagem",
  "ur": "Ek aur ride book karen", "hi": "एक और सवारी बुक करें", "bn": "আরেকটি রাইড বুক করুন"
};
NOEL_I18N["app.book_return"] = {
  "en": "Book your return trip", "es": "Reserva tu viaje de regreso", "fr": "Réservez votre trajet retour",
  "ar": "احجز رحلة عودتك", "pt": "Reserve sua viagem de volta",
  "ur": "Apni return trip book karen", "hi": "अपनी वापसी यात्रा बुक करें", "bn": "আপনার ফেরার যাত্রা বুক করুন"
};
NOEL_I18N["app.support_heading"] = {
  "en": "How can we help?", "es": "¿Cómo podemos ayudarte?", "fr": "Comment pouvons-nous vous aider ?",
  "ar": "كيف يمكننا مساعدتك؟", "pt": "Como podemos ajudar?",
  "ur": "Hum kaise madad kar sakte hain?", "hi": "हम कैसे मदद कर सकते हैं?", "bn": "আমরা কীভাবে সাহায্য করতে পারি?"
};
NOEL_I18N["app.support_text"] = {
  "en": "Email us at info@noelchauffer.com or send us a message below.",
  "es": "Escríbenos a info@noelchauffer.com o envíanos un mensaje abajo.",
  "fr": "Écrivez-nous à info@noelchauffer.com ou envoyez-nous un message ci-dessous.",
  "ar": "راسلنا على info@noelchauffer.com أو أرسل لنا رسالة أدناه.",
  "pt": "Envie um e-mail para info@noelchauffer.com ou envie-nos uma mensagem abaixo.",
  "ur": "Hamein info@noelchauffer.com par email karen ya neeche message bhejen.",
  "hi": "हमें info@noelchauffer.com पर ईमेल करें या नीचे संदेश भेजें।",
  "bn": "info@noelchauffer.com-এ ইমেইল করুন বা নিচে বার্তা পাঠান।"
};
NOEL_I18N["app.chat_placeholder"] = {
  "en": "Type a message…", "es": "Escribe un mensaje…", "fr": "Écrivez un message…",
  "ar": "اكتب رسالة…", "pt": "Digite uma mensagem…",
  "ur": "Message likhen…", "hi": "संदेश लिखें…", "bn": "বার্তা লিখুন…"
};
NOEL_I18N["app.send"] = {
  "en": "Send", "es": "Enviar", "fr": "Envoyer",
  "ar": "إرسال", "pt": "Enviar",
  "ur": "Send", "hi": "भेजें", "bn": "পাঠান"
};
NOEL_I18N["app.chat_language"] = {
  "en": "Chat language", "es": "Idioma del chat", "fr": "Langue du chat",
  "ar": "لغة المحادثة", "pt": "Idioma do chat",
  "ur": "Chat ki language", "hi": "चैट की भाषा", "bn": "চ্যাটের ভাষা"
};
NOEL_I18N["app.no_rides"] = {
  "en": "No rides yet.", "es": "Aún no hay viajes.", "fr": "Aucun trajet pour le moment.",
  "ar": "لا توجد رحلات بعد.", "pt": "Nenhuma viagem ainda.",
  "ur": "Abhi koi rides nahi hain.", "hi": "अभी कोई सवारी नहीं है।", "bn": "এখনো কোনো রাইড নেই।"
};
NOEL_I18N["app.finding_driver"] = {
  "en": "Finding your chauffeur", "es": "Buscando tu chófer", "fr": "Recherche de votre chauffeur",
  "ar": "جارٍ البحث عن سائقك", "pt": "Procurando seu motorista",
  "ur": "Aapka chauffeur dhoondha ja raha hai", "hi": "आपका शॉफ़र खोजा जा रहा है", "bn": "আপনার শোফার খোঁজা হচ্ছে"
};
NOEL_I18N["app.your_chauffeur"] = {
  "en": "Your chauffeur", "es": "Tu chófer", "fr": "Votre chauffeur",
  "ar": "سائقك", "pt": "Seu motorista",
  "ur": "Aapka chauffeur", "hi": "आपका शॉफ़र", "bn": "আপনার শোফার"
};
NOEL_I18N["app.live_map"] = {
  "en": "Live map", "es": "Mapa en vivo", "fr": "Carte en direct",
  "ar": "الخريطة المباشرة", "pt": "Mapa ao vivo",
  "ur": "Live map", "hi": "लाइव मैप", "bn": "লাইভ মানচিত্র"
};
NOEL_I18N["app.arrives"] = {
  "en": "arrives", "es": "llega", "fr": "arrive",
  "ar": "يصل", "pt": "chega",
  "ur": "aata hai", "hi": "पहुँचता है", "bn": "আসছে"
};
NOEL_I18N["app.driver_heading"] = {
  "en": "Driver is heading to you", "es": "El chófer viene hacia ti",
  "fr": "Le chauffeur vient vers vous",
  "ar": "السائق في طريقه إليك", "pt": "O motorista está indo até você",
  "ur": "Driver aapki taraf aa raha hai", "hi": "ड्राइवर आपकी ओर आ रहा है", "bn": "ড্রাইভার আপনার দিকে আসছেন"
};
NOEL_I18N["app.cancelled"] = {
  "en": "Cancelled", "es": "Cancelado", "fr": "Annulé",
  "ar": "ملغاة", "pt": "Cancelado",
  "ur": "Cancel", "hi": "रद्द", "bn": "বাতিল"
};
NOEL_I18N["app.completed"] = {
  "en": "Completed", "es": "Completado", "fr": "Terminé",
  "ar": "مكتملة", "pt": "Concluído",
  "ur": "Completed", "hi": "पूर्ण", "bn": "সম্পূর্ণ"
};
NOEL_I18N["app.sign_in"] = {
  "en": "Sign in", "es": "Iniciar sesión", "fr": "Se connecter",
  "ar": "تسجيل الدخول", "pt": "Entrar",
  "ur": "Sign in", "hi": "साइन इन करें", "bn": "সাইন ইন করুন"
};
NOEL_I18N["app.language"] = {
  "en": "Language", "es": "Idioma", "fr": "Langue",
  "ar": "اللغة", "pt": "Idioma",
  "ur": "Language", "hi": "भाषा", "bn": "ভাষা"
};
NOEL_I18N["lang.no_results"] = {
  "en": "No language found", "es": "No se encontró ningún idioma", "fr": "Aucune langue trouvée",
  "ar": "لم يتم العثور على لغة", "pt": "Nenhum idioma encontrado",
  "ur": "Koi language nahi mili", "hi": "कोई भाषा नहीं मिली", "bn": "কোনো ভাষা পাওয়া যায়নি"
};
NOEL_I18N["app.search_language"] = {
  "en": "Search language…", "es": "Buscar idioma…", "fr": "Rechercher une langue…",
  "ar": "ابحث عن لغة…", "pt": "Buscar idioma…",
  "ur": "Language search karen…", "hi": "भाषा खोजें…", "bn": "ভাষা খুঁজুন…"
};

/* ---- "Chat with us" widget ---- */
NOEL_I18N["chat.reply_24"] = {
  "en": "We reply within 24 hours.", "es": "Respondemos en un plazo de 24 horas.",
  "fr": "Nous répondons sous 24 heures.",
  "ar": "نرد خلال 24 ساعة.", "pt": "Respondemos em até 24 horas.",
  "ur": "Hum 24 hours ke andar reply karte hain.", "hi": "हम 24 घंटों के भीतर जवाब देते हैं।", "bn": "আমরা ২৪ ঘণ্টার মধ্যে উত্তর দিই।"
};
NOEL_I18N["chat.chip_book"] = {
  "en": "How do I book?", "es": "¿Cómo reservo?", "fr": "Comment réserver ?",
  "ar": "كيف أحجز؟", "pt": "Como reservo?",
  "ur": "Book kaise karen?", "hi": "बुक कैसे करें?", "bn": "কীভাবে বুক করব?"
};
NOEL_I18N["chat.chip_paused"] = {
  "en": "Are bookings paused?", "es": "¿Están en pausa las reservas?", "fr": "Les réservations sont-elles suspendues ?",
  "ar": "هل الحجوزات متوقفة؟", "pt": "As reservas estão pausadas?",
  "ur": "Kya bookings paused hain?", "hi": "क्या बुकिंग रुकी हुई हैं?", "bn": "বুকিং কি থেমে আছে?"
};
NOEL_I18N["chat.chip_cancel"] = {
  "en": "Cancellation rules", "es": "Reglas de cancelación", "fr": "Règles d'annulation",
  "ar": "قواعد الإلغاء", "pt": "Regras de cancelamento",
  "ur": "Cancellation rules", "hi": "रद्द करने के नियम", "bn": "বাতিলের নিয়ম"
};
NOEL_I18N["chat.chip_waiting"] = {
  "en": "Waiting time", "es": "Tiempo de espera", "fr": "Temps d'attente",
  "ar": "وقت الانتظار", "pt": "Tempo de espera",
  "ur": "Waiting time", "hi": "प्रतीक्षा समय", "bn": "অপেক্ষার সময়"
};
NOEL_I18N["chat.chip_lost"] = {
  "en": "Lost item", "es": "Objeto perdido", "fr": "Objet perdu",
  "ar": "غرض مفقود", "pt": "Objeto perdido",
  "ur": "Lost item", "hi": "खोया सामान", "bn": "হারানো জিনিস"
};
NOEL_I18N["chat.title"] = {
  "en": "Chat with us", "es": "Chatea con nosotros", "fr": "Discutez avec nous",
  "ar": "تحدث معنا", "pt": "Fale conosco",
  "ur": "Hum se chat karen", "hi": "हमसे चैट करें", "bn": "আমাদের সঙ্গে চ্যাট করুন"
};
NOEL_I18N["chat.greeting_app"] = {
  "en": "Hello, and welcome to Noel Chauffer. How can I help — booking, cancellation, waiting time, or something about a ride?",
  "es": "Hola, bienvenido a Noel Chauffer. ¿Cómo puedo ayudarte: reserva, cancelación, tiempo de espera o algo sobre un viaje?",
  "fr": "Bonjour et bienvenue chez Noel Chauffer. Comment puis-je vous aider — réservation, annulation, temps d'attente ou autre chose sur un trajet ?",
  "ar": "مرحبًا بك في نويل شوفير. كيف يمكنني مساعدتك — الحجز أو الإلغاء أو وقت الانتظار أو شيء عن رحلة؟",
  "pt": "Olá, bem-vindo à Noel Chauffer. Como posso ajudar — reserva, cancelamento, tempo de espera ou algo sobre uma viagem?",
  "ur": "Hello, Noel Chauffer mein welcome. Main kaise madad kar sakta hoon — booking, cancellation, waiting time, ya ride ke baare mein kuch?",
  "hi": "नमस्ते, नोएल शॉफ़र में स्वागत है। मैं कैसे मदद कर सकता हूँ — बुकिंग, रद्दीकरण, प्रतीक्षा समय, या सवारी के बारे में कुछ?",
  "bn": "হ্যালো, নোয়েল শোফারে স্বাগতম। আমি কীভাবে সাহায্য করতে পারি — বুকিং, বাতিল, অপেক্ষার সময়, বা রাইড সম্পর্কে কিছু?"
};
NOEL_I18N["chat.ans_price_app"] = {
  "en": "Enter your pickup and drop-off in the Book tab, choose your experience, and you will see the total for each class before you pay.",
  "es": "Escribe tu recogida y destino en la pestaña Reservar, elige tu experiencia y verás el total de cada clase antes de pagar.",
  "fr": "Saisissez votre lieu de prise en charge et votre destination dans l'onglet Réserver, choisissez votre expérience et vous verrez le total de chaque classe avant de payer.",
  "ar": "أدخل مكان الاستلام والوصول في تبويب الحجز، واختر تجربتك، وسترى المجموع لكل فئة قبل الدفع.",
  "pt": "Informe embarque e destino na aba Reservar, escolha sua experiência e você verá o total de cada classe antes de pagar.",
  "ur": "Book tab mein apna pickup aur drop-off likhen, apna experience chunen, aur pay karne se pehle har class ka total dekh lenge.",
  "hi": "बुक टैब में अपना पिकअप और ड्रॉप-ऑफ़ लिखें, अपना अनुभव चुनें, और भुगतान से पहले आप हर श्रेणी का कुल देखेंगे।",
  "bn": "বুক ট্যাবে আপনার পিকআপ ও ড্রপ-অফ লিখুন, আপনার অভিজ্ঞতা বেছে নিন, এবং পেমেন্টের আগে প্রতিটি শ্রেণির মোট দেখতে পাবেন।"
};
NOEL_I18N["chat.ans_driver_app"] = {
  "en": "As soon as your chauffeur accepts, you will see their name, phone number, car, colour and plate number in the My Rides tab — and the same details are sent to your phone and email.",
  "es": "En cuanto tu chófer acepte, verás su nombre, número de teléfono, coche, color y matrícula en la pestaña Mis viajes, y los mismos datos se enviarán a tu teléfono y correo.",
  "fr": "Dès que votre chauffeur accepte, vous verrez son nom, son numéro de téléphone, sa voiture, sa couleur et sa plaque dans l'onglet Mes trajets — et ces mêmes informations seront envoyées sur votre téléphone et par e-mail.",
  "ar": "بمجرد أن يقبل سائقك، سترى اسمه ورقم هاتفه وسيارته ولونها ورقم لوحتها في تبويب رحلاتي — وستُرسل التفاصيل نفسها إلى هاتفك وبريدك الإلكتروني.",
  "pt": "Assim que seu motorista aceitar, você verá o nome, o telefone, o carro, a cor e a placa dele na aba Minhas viagens — e os mesmos dados serão enviados para seu telefone e e-mail.",
  "ur": "Jaise hi aapka chauffeur accept karega, aapko My Rides tab mein unka naam, phone number, gaadi, colour aur plate number dikhega — aur yehi details aapke phone aur email par bhi bheji jayengi.",
  "hi": "जैसे ही आपका शॉफ़र स्वीकार करेगा, आपको My Rides टैब में उनका नाम, फ़ोन नंबर, गाड़ी, रंग और नंबर प्लेट दिखेगा — और यही जानकारी आपके फ़ोन और ईमेल पर भी भेजी जाएगी।",
  "bn": "আপনার শোফার গ্রহণ করলেই My Rides ট্যাবে তাঁর নাম, ফোন নম্বর, গাড়ি, রং ও নম্বর প্লেট দেখতে পাবেন — আর একই বিবরণ আপনার ফোন ও ইমেইলে পাঠানো হবে।"
};
NOEL_I18N["chat.ans_return_app"] = {
  "en": "For a return journey, simply book a second one-way ride. After you pay for your first ride, the app offers you a return booking with the addresses already swapped for you.",
  "es": "Para el viaje de regreso, simplemente reserva un segundo viaje de ida. Después de pagar tu primer viaje, la app te ofrece una reserva de regreso con las direcciones ya intercambiadas.",
  "fr": "Pour le trajet retour, réservez simplement un deuxième trajet aller simple. Après avoir payé votre premier trajet, l'application vous propose une réservation retour avec les adresses déjà inversées.",
  "ar": "لرحلة العودة، ما عليك سوى حجز رحلة ذهاب ثانية. بعد دفعك لرحلتك الأولى، سيعرض لك التطبيق حجز عودة مع تبديل العناوين مسبقًا.",
  "pt": "Para a viagem de volta, basta reservar uma segunda viagem só de ida. Depois de pagar sua primeira viagem, o app oferece uma reserva de volta com os endereços já trocados.",
  "ur": "Return journey ke liye bas doosri one-way ride book karen. Pehli ride pay karne ke baad, app aapko return booking dega jisme addresses pehle se swap honge.",
  "hi": "वापसी यात्रा के लिए, बस दूसरी एकतरफ़ा सवारी बुक करें। अपनी पहली सवारी का भुगतान करने के बाद, ऐप आपको वापसी बुकिंग देगा जिसमें पते पहले से बदले हुए होंगे।",
  "bn": "ফেরার যাত্রার জন্য শুধু দ্বিতীয় একমুখী রাইড বুক করুন। প্রথম রাইডের পেমেন্টের পর অ্যাপ আপনাকে ফেরার বুকিং দেবে, যেখানে ঠিকানা আগেই বদলে দেওয়া থাকবে।"
};
NOEL_I18N["chat.ans_book_app"] = {
  "en": "Enter your pickup and drop-off, date and time in the Book tab, choose your experience, and pay by card — your chauffeur is assigned right after payment.",
  "es": "Escribe tu recogida y destino, fecha y hora en la pestaña Reservar, elige tu experiencia y paga con tarjeta: tu chófer se asigna justo después del pago.",
  "fr": "Saisissez votre lieu de prise en charge et votre destination, la date et l'heure dans l'onglet Réserver, choisissez votre expérience et payez par carte — votre chauffeur est assigné juste après le paiement.",
  "ar": "أدخل مكان الاستلام والوصول والتاريخ والوقت في تبويب الحجز، واختر تجربتك، وادفع بالبطاقة — وسيتم تعيين سائقك مباشرة بعد الدفع.",
  "pt": "Informe embarque e destino, data e hora na aba Reservar, escolha sua experiência e pague com cartão — seu motorista é designado logo após o pagamento.",
  "ur": "Book tab mein apna pickup aur drop-off, date aur time likhen, apna experience chunen, aur card se pay karen — payment ke foran baad aapka chauffeur assign ho jayega.",
  "hi": "बुक टैब में अपना पिकअप और ड्रॉप-ऑफ़, तारीख और समय लिखें, अपना अनुभव चुनें, और कार्ड से भुगतान करें — भुगतान के तुरंत बाद आपका शॉफ़र नियुक्त हो जाएगा।",
  "bn": "বুক ট্যাবে আপনার পিকআপ ও ড্রপ-অফ, তারিখ ও সময় লিখুন, আপনার অভিজ্ঞতা বেছে নিন, এবং কার্ডে পেমেন্ট করুন — পেমেন্টের পরপরই আপনার শোফার নিয়োগ করা হবে।"
};
NOEL_I18N["chat.greeting"] = {
  "en": "Hello, and welcome to Noel Chauffer. How can I help — cancellation, waiting time, or something about a ride?",
  "es": "Hola, bienvenido a Noel Chauffer. ¿Cómo puedo ayudarte: cancelación, tiempo de espera o algo sobre un viaje?",
  "fr": "Bonjour et bienvenue chez Noel Chauffer. Comment puis-je vous aider — annulation, temps d'attente ou autre chose sur un trajet ?",
  "ar": "مرحبًا بك في نويل شوفير. كيف يمكنني مساعدتك — الإلغاء أو وقت الانتظار أو شيء عن رحلة؟",
  "pt": "Olá, bem-vindo à Noel Chauffer. Como posso ajudar — cancelamento, tempo de espera ou algo sobre uma viagem?",
  "ur": "Hello, Noel Chauffer mein welcome. Main kaise madad kar sakta hoon — cancellation, waiting time, ya ride ke baare mein kuch?",
  "hi": "नमस्ते, नोएल शॉफ़र में स्वागत है। मैं कैसे मदद कर सकता हूँ — रद्दीकरण, प्रतीक्षा समय, या सवारी के बारे में कुछ?",
  "bn": "হ্যালো, নোয়েল শোফারে স্বাগতম। আমি কীভাবে সাহায্য করতে পারি — বাতিল, অপেক্ষার সময়, বা রাইড সম্পর্কে কিছু?"
};
NOEL_I18N["chat.ans_paused"] = {
  "en": "No — bookings are open. Enter your pickup and drop-off in the booking form to see your fare.",
  "es": "No, las reservas están abiertas. Escribe tu recogida y destino en el formulario de reserva para ver tu tarifa.",
  "fr": "Non — les réservations sont ouvertes. Saisissez votre lieu de prise en charge et votre destination dans le formulaire pour voir votre tarif.",
  "ar": "لا — الحجوزات مفتوحة. أدخل مكان الاستلام والوصول في نموذج الحجز لترى أجرتك.",
  "pt": "Não — as reservas estão abertas. Informe embarque e destino no formulário de reserva para ver sua tarifa.",
  "ur": "Nahi — bookings khuli hain. Apna pickup aur drop-off booking form mein likhen to fare dikhega.",
  "hi": "नहीं — बुकिंग खुली है। अपना किराया देखने के लिए बुकिंग फ़ॉर्म में पिकअप और ड्रॉप-ऑफ़ लिखें।",
  "bn": "না — বুকিং খোলা আছে। ভাড়া দেখতে বুকিং ফর্মে আপনার পিকআপ ও ড্রপ-অফ লিখুন।"
};
NOEL_I18N["chat.ans_cancel"] = {
  "en": "Cancellation is free if you cancel more than 1 hour before pickup. If you cancel 1 hour or less before pickup, the cancellation is not refundable.",
  "es": "La cancelación es gratis si cancelas más de 1 hora antes de la recogida. Si cancelas 1 hora o menos antes, no es reembolsable.",
  "fr": "L'annulation est gratuite si vous annulez plus d'1 heure avant la prise en charge. Si vous annulez 1 heure ou moins avant, elle n'est pas remboursable.",
  "ar": "الإلغاء مجاني إذا ألغيت قبل أكثر من ساعة من الاستلام. أما إذا ألغيت قبل ساعة أو أقل من الاستلام، فلا يُسترد المبلغ.",
  "pt": "O cancelamento é gratuito se você cancelar mais de 1 hora antes do embarque. Se cancelar 1 hora ou menos antes, não é reembolsável.",
  "ur": "Cancellation free hai agar aap pickup se 1 hour se zyada pehle cancel karen. Agar 1 hour ya us se kam pehle cancel karen to refund nahi milega.",
  "hi": "पिकअप से 1 घंटे से ज़्यादा पहले रद्द करने पर रद्दीकरण मुफ़्त है। यदि आप पिकअप से 1 घंटे या उससे कम पहले रद्द करते हैं, तो यह वापस नहीं होगा।",
  "bn": "পিকআপের ১ ঘণ্টার বেশি আগে বাতিল করলে বাতিল বিনামূল্যে। পিকআপের ১ ঘণ্টা বা তার কম আগে বাতিল করলে তা ফেরতযোগ্য নয়।"
};
NOEL_I18N["chat.ans_wait"] = {
  "en": "Waiting is free for 60 minutes at airports and 15 minutes at other pickups. After that, waiting charges apply.",
  "es": "La espera es gratis 60 minutos en aeropuertos y 15 minutos en otras recogidas. Después, se aplican cargos por espera.",
  "fr": "L'attente est gratuite pendant 60 minutes aux aéroports et 15 minutes aux autres prises en charge. Ensuite, des frais d'attente s'appliquent.",
  "ar": "الانتظار مجاني لمدة 60 دقيقة في المطارات و15 دقيقة في عمليات الاستلام الأخرى. بعد ذلك، تُطبق رسوم الانتظار.",
  "pt": "A espera é gratuita por 60 minutos em aeroportos e 15 minutos em outros embarques. Depois disso, taxas de espera se aplicam.",
  "ur": "Waiting airports par 60 minutes aur doosri pickups par 15 minutes free hai. Uske baad waiting charges lagte hain.",
  "hi": "एयरपोर्ट पर 60 मिनट और अन्य पिकअप पर 15 मिनट तक प्रतीक्षा मुफ़्त है। उसके बाद प्रतीक्षा शुल्क लगता है।",
  "bn": "বিমানবন্দরে ৬০ মিনিট এবং অন্যান্য পিকআপে ১৫ মিনিট পর্যন্ত অপেক্ষা বিনামূল্যে। এরপর অপেক্ষার চার্জ প্রযোজ্য।"
};
NOEL_I18N["chat.ans_price"] = {
  "en": "Enter your pickup and drop-off in the booking form above, choose your experience, and you will see the total for each class before you pay.",
  "es": "Escribe tu recogida y destino en el formulario de arriba, elige tu experiencia y verás el total de cada clase antes de pagar.",
  "fr": "Saisissez votre lieu de prise en charge et votre destination dans le formulaire ci-dessus, choisissez votre expérience et vous verrez le total de chaque classe avant de payer.",
  "ar": "أدخل مكان الاستلام والوصول في نموذج الحجز أعلاه، واختر تجربتك، وسترى المجموع لكل فئة قبل الدفع.",
  "pt": "Informe embarque e destino no formulário acima, escolha sua experiência e você verá o total de cada classe antes de pagar.",
  "ur": "Upar booking form mein apna pickup aur drop-off likhen, apna experience chunen, aur pay karne se pehle har class ka total dekh lenge.",
  "hi": "ऊपर बुकिंग फ़ॉर्म में अपना पिकअप और ड्रॉप-ऑफ़ लिखें, अपना अनुभव चुनें, और भुगतान से पहले आप हर श्रेणी का कुल देखेंगे।",
  "bn": "উপরের বুকিং ফর্মে আপনার পিকআপ ও ড্রপ-অফ লিখুন, আপনার অভিজ্ঞতা বেছে নিন, এবং পেমেন্টের আগে প্রতিটি শ্রেণির মোট দেখতে পাবেন।"
};
NOEL_I18N["chat.ans_lost"] = {
  "en": "I am sorry to hear that. Please report it here as soon as you can, and within 7 days. The driver checks the car after every ride. Unclaimed items go to the police station after one week.",
  "es": "Lamento oírlo. Repórtalo aquí lo antes posible, dentro de 7 días. El chófer revisa el coche después de cada viaje. Los objetos no reclamados van a la comisaría después de una semana.",
  "fr": "Je suis désolé d'apprendre cela. Veuillez le signaler ici dès que possible, sous 7 jours. Le chauffeur vérifie la voiture après chaque trajet. Les objets non réclamés sont remis au commissariat après une semaine.",
  "ar": "يؤسفني سماع ذلك. يرجى الإبلاغ عنه هنا في أقرب وقت ممكن وخلال 7 أيام. يفحص السائق السيارة بعد كل رحلة. وتُسلَّم الأغراض غير المطالب بها إلى مركز الشرطة بعد أسبوع.",
  "pt": "Sinto muito por isso. Relate aqui o quanto antes, em até 7 dias. O motorista verifica o carro após cada viagem. Itens não reclamados vão para a delegacia após uma semana.",
  "ur": "Sun kar afsos hua. Jitni jaldi ho sake yahin report karen, 7 din ke andar. Driver har ride ke baad gaadi check karta hai. Ek hafte ke baad bina daawe wali cheezein police station chali jati hain.",
  "hi": "यह सुनकर दुख हुआ। कृपया इसे जल्द से जल्द, 7 दिनों के भीतर, यहीं रिपोर्ट करें। ड्राइवर हर सवारी के बाद गाड़ी जाँचता है। एक सप्ताह बाद बिना दावे वाली चीज़ें पुलिस स्टेशन चली जाती हैं।",
  "bn": "শুনে দুঃখিত হলাম। যত তাড়াতাড়ি সম্ভব, ৭ দিনের মধ্যে এখানে জানান। ড্রাইভার প্রতিটি রাইডের পর গাড়ি পরীক্ষা করেন। এক সপ্তাহ পর দাবিহীন জিনিস থানায় পাঠানো হয়।"
};
NOEL_I18N["chat.ans_problem"] = {
  "en": "I am sorry about that. I will escalate this to the owner, who will look into it personally. Please tell me your pickup date and time and what happened.",
  "es": "Lo siento. Escalaré esto al propietario, que lo revisará personalmente. Dime la fecha y hora de tu recogida y qué pasó.",
  "fr": "Je suis désolé. Je vais transmettre cela au propriétaire, qui s'en occupera personnellement. Indiquez-moi la date et l'heure de votre prise en charge et ce qui s'est passé.",
  "ar": "أنا آسف لذلك. سأصعّد الأمر إلى المالك، الذي سينظر فيه بنفسه. يرجى إخباري بتاريخ ووقت الاستلام وما حدث.",
  "pt": "Sinto muito por isso. Vou escalar para o proprietário, que vai analisar pessoalmente. Informe a data e a hora do embarque e o que aconteceu.",
  "ur": "Is ke liye maazrat. Main ye owner tak pahuncha doonga, jo khud dekhenge. Apni pickup ki date aur time aur kya hua, ye bata den.",
  "hi": "इसके लिए खेद है। मैं इसे मालिक तक पहुँचाऊँगा, जो इसे व्यक्तिगत रूप से देखेंगे। कृपया अपनी पिकअप तिथि और समय तथा क्या हुआ, बताएँ।",
  "bn": "এর জন্য দুঃখিত। আমি এটি মালিকের কাছে পাঠাব, যিনি নিজে দেখবেন। আপনার পিকআপের তারিখ ও সময় এবং কী ঘটেছে তা জানান।"
};
NOEL_I18N["chat.ans_driver"] = {
  "en": "As soon as your chauffeur accepts, you will see their name, phone number, car, colour and plate number on this page — and the same details are sent to your phone and email.",
  "es": "En cuanto tu chófer acepte, verás su nombre, número de teléfono, coche, color y matrícula en esta página, y los mismos datos se enviarán a tu teléfono y correo.",
  "fr": "Dès que votre chauffeur accepte, vous verrez son nom, son numéro de téléphone, sa voiture, sa couleur et sa plaque sur cette page — et ces mêmes informations seront envoyées sur votre téléphone et par e-mail.",
  "ar": "بمجرد أن يقبل سائقك، سترى اسمه ورقم هاتفه وسيارته ولونها ورقم لوحتها على هذه الصفحة — وستُرسل التفاصيل نفسها إلى هاتفك وبريدك الإلكتروني.",
  "pt": "Assim que seu motorista aceitar, você verá o nome, o telefone, o carro, a cor e a placa dele nesta página — e os mesmos dados serão enviados para seu telefone e e-mail.",
  "ur": "Jaise hi aapka chauffeur accept karega, aapko is page par unka naam, phone number, gaadi, colour aur plate number dikhega — aur yehi details aapke phone aur email par bhi bheji jayengi.",
  "hi": "जैसे ही आपका शॉफ़र स्वीकार करेगा, आपको इस पेज पर उनका नाम, फ़ोन नंबर, गाड़ी, रंग और नंबर प्लेट दिखेगा — और यही जानकारी आपके फ़ोन और ईमेल पर भी भेजी जाएगी।",
  "bn": "আপনার শোফার গ্রহণ করলেই এই পাতায় তাঁর নাম, ফোন নম্বর, গাড়ি, রং ও নম্বর প্লেট দেখতে পাবেন — আর একই বিবরণ আপনার ফোন ও ইমেইলে পাঠানো হবে।"
};
NOEL_I18N["chat.ans_car"] = {
  "en": "Our rides come in three classes — Business Class, Business SUV and First Class — recent high-end cars, clean, comfortable, and prepared for every ride, with phone chargers on board.",
  "es": "Nuestros viajes vienen en tres clases: Business Class, Business SUV y First Class. Coches recientes de alta gama, limpios, cómodos y preparados para cada viaje, con cargadores de teléfono a bordo.",
  "fr": "Nos trajets existent en trois classes — Business Class, Business SUV et First Class — des voitures récentes haut de gamme, propres, confortables et préparées pour chaque trajet, avec des chargeurs de téléphone à bord.",
  "ar": "رحلاتنا تأتي في ثلاث فئات — Business Class وBusiness SUV وFirst Class — سيارات حديثة فاخرة، نظيفة ومريحة ومجهزة لكل رحلة، مع شواحن هواتف على متنها.",
  "pt": "Nossas viagens têm três classes — Business Class, Business SUV e First Class — carros recentes de alto padrão, limpos, confortáveis e preparados para cada viagem, com carregadores de celular a bordo.",
  "ur": "Hamari rides teen classes mein aati hain — Business Class, Business SUV aur First Class — nayi high-end gaadiyan, saaf, aaramdeh, har ride ke liye ready, aur onboard phone chargers ke saath.",
  "hi": "हमारी सवारियाँ तीन श्रेणियों में आती हैं — Business Class, Business SUV और First Class — नई उच्च-स्तरीय गाड़ियाँ, साफ़, आरामदायक, हर सवारी के लिए तैयार, और ऑनबोर्ड फ़ोन चार्जर के साथ।",
  "bn": "আমাদের রাইড তিনটি শ্রেণিতে আসে — Business Class, Business SUV ও First Class — নতুন উঁচুমানের গাড়ি, পরিষ্কার, আরামদায়ক, প্রতিটি রাইডের জন্য প্রস্তুত, এবং অনবোর্ড ফোন চার্জারসহ।"
};
NOEL_I18N["chat.ans_return"] = {
  "en": "For a return journey, simply book a second one-way ride. After you pay for your first ride, this page offers you a return booking with the addresses already swapped for you.",
  "es": "Para el viaje de regreso, simplemente reserva un segundo viaje de ida. Después de pagar tu primer viaje, esta página te ofrece una reserva de regreso con las direcciones ya intercambiadas.",
  "fr": "Pour le trajet retour, réservez simplement un deuxième trajet aller simple. Après avoir payé votre premier trajet, cette page vous propose une réservation retour avec les adresses déjà inversées.",
  "ar": "لرحلة العودة، ما عليك سوى حجز رحلة ذهاب ثانية. بعد دفعك لرحلتك الأولى، ستعرض لك هذه الصفحة حجز عودة مع تبديل العناوين مسبقًا.",
  "pt": "Para a viagem de volta, basta reservar uma segunda viagem só de ida. Depois de pagar sua primeira viagem, esta página oferece uma reserva de volta com os endereços já trocados.",
  "ur": "Return journey ke liye bas doosri one-way ride book karen. Pehli ride pay karne ke baad, ye page aapko return booking dega jisme addresses pehle se swap honge.",
  "hi": "वापसी यात्रा के लिए, बस दूसरी एकतरफ़ा सवारी बुक करें। अपनी पहली सवारी का भुगतान करने के बाद, यह पेज आपको वापसी बुकिंग देगा जिसमें पते पहले से बदले हुए होंगे।",
  "bn": "ফেরার যাত্রার জন্য শুধু দ্বিতীয় একমুখী রাইড বুক করুন। প্রথম রাইডের পেমেন্টের পর এই পাতায় ফেরার বুকিং পাবেন, যেখানে ঠিকানা আগেই বদলে দেওয়া থাকবে।"
};
NOEL_I18N["chat.ans_hourly"] = {
  "en": "Choose the “By the hour” tab in the booking form, pick a vehicle class and how many hours you need (minimum 2 hours). Your chauffeur stays with you for the hours you book, with 25 miles of travel included per hour.",
  "es": "Elige la pestaña «Por horas» en el formulario de reserva, escoge una clase de vehículo y cuántas horas necesitas (mínimo 2 horas). Tu chófer se queda contigo las horas que reserves, con 25 millas de viaje incluidas por hora.",
  "fr": "Choisissez l'onglet « À l'heure » dans le formulaire de réservation, sélectionnez une classe de véhicule et le nombre d'heures nécessaires (minimum 2 heures). Votre chauffeur reste avec vous pendant les heures réservées, avec 25 miles de trajet inclus par heure.",
  "ar": "اختر تبويب «بالساعة» في نموذج الحجز، واختر فئة المركبة وعدد الساعات التي تحتاجها (الحد الأدنى ساعتان). يبقى سائقك معك طوال الساعات التي تحجزها، مع 25 ميلًا من السفر مشمولة في الساعة.",
  "pt": "Escolha a aba “Por hora” no formulário de reserva, selecione uma classe de veículo e quantas horas você precisa (mínimo de 2 horas). Seu motorista fica com você pelas horas reservadas, com 25 milhas de viagem incluídas por hora.",
  "ur": "Booking form mein “By the hour” tab chunen, gaadi ki class aur kitne hours chahiye ye chunen (minimum 2 hours). Aapka chauffeur utne hours aapke saath rahega, har hour mein 25 miles travel shamil hai.",
  "hi": "बुकिंग फ़ॉर्म में “By the hour” टैब चुनें, वाहन की श्रेणी और कितने घंटे चाहिए, यह चुनें (न्यूनतम 2 घंटे)। आपका शॉफ़र आपके बुक किए घंटों तक आपके साथ रहेगा, प्रति घंटे 25 मील की यात्रा शामिल है।",
  "bn": "বুকিং ফর্মে “By the hour” ট্যাব বেছে নিন, গাড়ির শ্রেণি ও কত ঘণ্টা দরকার তা বেছে নিন (সর্বনিম্ন ২ ঘণ্টা)। আপনার শোফার আপনার বুক করা ঘণ্টাগুলো আপনার সঙ্গে থাকবেন, প্রতি ঘণ্টায় ২৫ মাইল ভ্রমণ অন্তর্ভুক্ত।"
};
NOEL_I18N["chat.ans_refer"] = {
  "en": "If a friend referred you, open their referral link — it takes you to the booking form with their code already filled in, and your first booking gets 5% off.",
  "es": "Si un amigo te recomendó, abre su enlace de recomendación: te lleva al formulario de reserva con su código ya rellenado, y tu primera reserva tiene un 5 % de descuento.",
  "fr": "Si un ami vous a parrainé, ouvrez son lien de parrainage — il vous mène au formulaire de réservation avec son code déjà rempli, et votre première réservation bénéficie de 5 % de réduction.",
  "ar": "إذا أحالك صديق، افتح رابط الإحالة الخاص به — سيأخذك إلى نموذج الحجز ورمزه معبأ مسبقًا، وستحصل على خصم 5٪ على حجزك الأول.",
  "pt": "Se um amigo indicou você, abra o link de indicação dele — ele leva ao formulário de reserva com o código já preenchido, e sua primeira reserva tem 5% de desconto.",
  "ur": "Agar kisi dost ne refer kiya hai to unka referral link kholen — wo aapko booking form par le jayega jisme unka code pehle se bhara hoga, aur aapki pehli booking par 5% off milega.",
  "hi": "यदि किसी मित्र ने आपको रेफ़र किया है, तो उनका रेफ़रल लिंक खोलें — यह आपको बुकिंग फ़ॉर्म पर ले जाएगा जिसमें उनका कोड पहले से भरा होगा, और आपकी पहली बुकिंग पर 5% की छूट मिलेगी।",
  "bn": "যদি কোনো বন্ধু আপনাকে রেফার করে থাকেন, তাঁর রেফারেল লিংক খুলুন — এটি আপনাকে বুকিং ফর্মে নিয়ে যাবে যেখানে তাঁর কোড আগেই ভরা থাকবে, এবং আপনার প্রথম বুকিংয়ে ৫% ছাড় পাবেন।"
};
NOEL_I18N["chat.ans_book"] = {
  "en": "Enter your pickup and drop-off, date and time in the booking form above, choose your experience, and pay by card — your chauffeur is assigned right after payment.",
  "es": "Escribe tu recogida y destino, fecha y hora en el formulario de arriba, elige tu experiencia y paga con tarjeta: tu chófer se asigna justo después del pago.",
  "fr": "Saisissez votre lieu de prise en charge et votre destination, la date et l'heure dans le formulaire ci-dessus, choisissez votre expérience et payez par carte — votre chauffeur est assigné juste après le paiement.",
  "ar": "أدخل مكان الاستلام والوصول والتاريخ والوقت في نموذج الحجز أعلاه، واختر تجربتك، وادفع بالبطاقة — وسيتم تعيين سائقك مباشرة بعد الدفع.",
  "pt": "Informe embarque e destino, data e hora no formulário acima, escolha sua experiência e pague com cartão — seu motorista é designado logo após o pagamento.",
  "ur": "Upar booking form mein apna pickup aur drop-off, date aur time likhen, apna experience chunen, aur card se pay karen — payment ke foran baad aapka chauffeur assign ho jayega.",
  "hi": "ऊपर बुकिंग फ़ॉर्म में अपना पिकअप और ड्रॉप-ऑफ़, तारीख और समय लिखें, अपना अनुभव चुनें, और कार्ड से भुगतान करें — भुगतान के तुरंत बाद आपका शॉफ़र नियुक्त हो जाएगा।",
  "bn": "উপরের বুকিং ফর্মে আপনার পিকআপ ও ড্রপ-অফ, তারিখ ও সময় লিখুন, আপনার অভিজ্ঞতা বেছে নিন, এবং কার্ডে পেমেন্ট করুন — পেমেন্টের পরপরই আপনার শোফার নিয়োগ করা হবে।"
};
NOEL_I18N["chat.ans_hello"] = {
  "en": "Hello, and welcome to Noel Chauffer. Bookings are open — enter your pickup and drop-off in the booking form to see your fare. I can still help with prices, cancellation, waiting time, lost items, or a problem with a ride.",
  "es": "Hola, bienvenido a Noel Chauffer. Las reservas están abiertas: escribe tu recogida y destino en el formulario para ver tu tarifa. También puedo ayudarte con precios, cancelación, tiempo de espera, objetos perdidos o un problema con un viaje.",
  "fr": "Bonjour et bienvenue chez Noel Chauffer. Les réservations sont ouvertes — saisissez votre lieu de prise en charge et votre destination dans le formulaire pour voir votre tarif. Je peux aussi vous aider avec les prix, l'annulation, le temps d'attente, les objets perdus ou un problème avec un trajet.",
  "ar": "مرحبًا بك في نويل شوفير. الحجوزات مفتوحة — أدخل مكان الاستلام والوصول في نموذج الحجز لترى أجرتك. ويمكنني أيضًا مساعدتك في الأسعار أو الإلغاء أو وقت الانتظار أو الأغراض المفقودة أو مشكلة في رحلة.",
  "pt": "Olá, bem-vindo à Noel Chauffer. As reservas estão abertas — informe embarque e destino no formulário para ver sua tarifa. Também posso ajudar com preços, cancelamento, tempo de espera, objetos perdidos ou um problema com uma viagem.",
  "ur": "Hello, Noel Chauffer mein welcome. Bookings khuli hain — apna pickup aur drop-off booking form mein likhen to fare dikhega. Main prices, cancellation, waiting time, lost items, ya ride ki kisi problem mein bhi madad kar sakta hoon.",
  "hi": "नमस्ते, नोएल शॉफ़र में स्वागत है। बुकिंग खुली है — अपना किराया देखने के लिए बुकिंग फ़ॉर्म में पिकअप और ड्रॉप-ऑफ़ लिखें। मैं कीमतों, रद्दीकरण, प्रतीक्षा समय, खोए सामान, या सवारी की किसी समस्या में भी मदद कर सकता हूँ।",
  "bn": "হ্যালো, নোয়েল শোফারে স্বাগতম। বুকিং খোলা আছে — ভাড়া দেখতে বুকিং ফর্মে আপনার পিকআপ ও ড্রপ-অফ লিখুন। আমি দাম, বাতিল, অপেক্ষার সময়, হারানো জিনিস, বা রাইডের কোনো সমস্যায়ও সাহায্য করতে পারি।"
};
NOEL_I18N["chat.ans_human"] = {
  "en": "You are chatting with the Noel Chauffer team here. The team replies within 24 hours. If your matter is urgent, please describe it here and we will escalate it to the owner.",
  "es": "Estás chateando aquí con el equipo de Noel Chauffer. El equipo responde en un plazo de 24 horas. Si tu asunto es urgente, descríbelo aquí y lo escalaremos al propietario.",
  "fr": "Vous discutez ici avec l'équipe Noel Chauffer. L'équipe répond sous 24 heures. Si votre demande est urgente, décrivez-la ici et nous la transmettrons au propriétaire.",
  "ar": "أنت تتحدث هنا مع فريق نويل شوفير. يرد الفريق خلال 24 ساعة. إذا كان أمرك عاجلًا، فصِفه هنا وسنصعّده إلى المالك.",
  "pt": "Você está conversando aqui com a equipe da Noel Chauffer. A equipe responde em até 24 horas. Se o assunto for urgente, descreva-o aqui e vamos escalar para o proprietário.",
  "ur": "Aap yahan Noel Chauffer team se chat kar rahe hain. Team 24 hours ke andar reply karti hai. Agar aapka kaam urgent hai to yahin likhen, hum owner tak pahuncha denge.",
  "hi": "आप यहाँ नोएल शॉफ़र टीम से चैट कर रहे हैं। टीम 24 घंटों के भीतर जवाब देती है। यदि आपका मामला ज़रूरी है, तो कृपया इसे यहाँ बताएँ और हम इसे मालिक तक पहुँचाएँगे।",
  "bn": "আপনি এখানে নোয়েল শোফার টিমের সঙ্গে চ্যাট করছেন। টিম ২৪ ঘণ্টার মধ্যে উত্তর দেয়। বিষয়টি জরুরি হলে এখানে বর্ণনা করুন, আমরা মালিকের কাছে পাঠাব।"
};
NOEL_I18N["chat.ans_default"] = {
  "en": "Happy to help. Bookings are open. I can answer questions about prices, cancellation, waiting time, your chauffeur's details, cars, return trips, by-the-hour rides, or lost items — just ask.",
  "es": "Encantado de ayudar. Las reservas están abiertas. Puedo responder preguntas sobre precios, cancelación, tiempo de espera, los datos de tu chófer, coches, viajes de regreso, viajes por horas u objetos perdidos: solo pregunta.",
  "fr": "Avec plaisir. Les réservations sont ouvertes. Je peux répondre à vos questions sur les prix, l'annulation, le temps d'attente, les coordonnées de votre chauffeur, les voitures, les trajets retour, les trajets à l'heure ou les objets perdus — demandez simplement.",
  "ar": "يسعدني المساعدة. الحجوزات مفتوحة. يمكنني الإجابة عن أسئلة حول الأسعار أو الإلغاء أو وقت الانتظار أو بيانات سائقك أو السيارات أو رحلات العودة أو الرحلات بالساعة أو الأغراض المفقودة — فقط اسأل.",
  "pt": "Prazer em ajudar. As reservas estão abertas. Posso responder perguntas sobre preços, cancelamento, tempo de espera, dados do seu motorista, carros, viagens de volta, viagens por hora ou objetos perdidos — é só perguntar.",
  "ur": "Madad karke khushi hogi. Bookings khuli hain. Main prices, cancellation, waiting time, aapke chauffeur ki details, gaadiyan, return trips, by-the-hour rides, ya lost items ke baare mein jawab de sakta hoon — bas poochhen.",
  "hi": "मदद करके खुशी होगी। बुकिंग खुली है। मैं कीमतों, रद्दीकरण, प्रतीक्षा समय, आपके शॉफ़र के विवरण, गाड़ियों, वापसी यात्राओं, घंटे के हिसाब से सवारी, या खोए सामान के बारे में जवाब दे सकता हूँ — बस पूछें।",
  "bn": "সাহায্য করতে পেরে খুশি। বুকিং খোলা আছে। আমি দাম, বাতিল, অপেক্ষার সময়, আপনার শোফারের বিবরণ, গাড়ি, ফেরার যাত্রা, ঘণ্টা হিসেবে রাইড, বা হারানো জিনিস সম্পর্কে উত্তর দিতে পারি — শুধু জিজ্ঞেস করুন।"
};
NOEL_I18N["chat.placeholder"] = {
  "en": "Type your message…", "es": "Escribe tu mensaje…", "fr": "Écrivez votre message…",
  "ar": "اكتب رسالتك…", "pt": "Digite sua mensagem…",
  "ur": "Apna message likhen…", "hi": "अपना संदेश लिखें…", "bn": "আপনার বার্তা লিখুন…"
};
NOEL_I18N["chat.send"] = {
  "en": "Send", "es": "Enviar", "fr": "Envoyer",
  "ar": "إرسال", "pt": "Enviar",
  "ur": "Send", "hi": "भेजें", "bn": "পাঠান"
};
NOEL_I18N["chat.book_ride"] = {
  "en": "Book a ride", "es": "Reservar un viaje", "fr": "Réserver un trajet",
  "ar": "احجز رحلة", "pt": "Reservar uma viagem",
  "ur": "Ride book karen", "hi": "सवारी बुक करें", "bn": "রাইড বুক করুন"
};
NOEL_I18N["chat.hours"] = {
  "en": "Our hours", "es": "Nuestro horario", "fr": "Nos horaires",
  "ar": "ساعات عملنا", "pt": "Nosso horário",
  "ur": "Hamare hours", "hi": "हमारा समय", "bn": "আমাদের সময়"
};
NOEL_I18N["chat.service_area"] = {
  "en": "Service area", "es": "Zona de servicio", "fr": "Zone de service",
  "ar": "منطقة الخدمة", "pt": "Área de atendimento",
  "ur": "Service area", "hi": "सेवा क्षेत्र", "bn": "পরিষেবা এলাকা"
};
NOEL_I18N["chat.contact"] = {
  "en": "Contact us", "es": "Contáctanos", "fr": "Contactez-nous",
  "ar": "اتصل بنا", "pt": "Fale conosco",
  "ur": "Hum se rabta karen", "hi": "हमसे संपर्क करें", "bn": "আমাদের সঙ্গে যোগাযোগ করুন"
};
NOEL_I18N["chat.more_options"] = {
  "en": "More options", "es": "Más opciones", "fr": "Plus d'options",
  "ar": "خيارات أخرى", "pt": "Mais opções",
  "ur": "Aur options", "hi": "और विकल्प", "bn": "আরও বিকল্প"
};
NOEL_I18N["chat.new_message"] = {
  "en": "New message", "es": "Nuevo mensaje", "fr": "Nouveau message",
  "ar": "رسالة جديدة", "pt": "Nova mensagem",
  "ur": "Naya message", "hi": "नया संदेश", "bn": "নতুন বার্তা"
};

/* ---- Hourly ---- */
NOEL_I18N["hourly.title"] = {
  "en": "Hourly hire", "es": "Alquiler por horas", "fr": "Location à l'heure",
  "ar": "الحجز بالساعة", "pt": "Aluguel por hora",
  "ur": "Hourly hire", "hi": "घंटे के हिसाब से किराया", "bn": "ঘণ্টা হিসেবে ভাড়া"
};
NOEL_I18N["hourly.hours"] = {
  "en": "Hours", "es": "Horas", "fr": "Heures",
  "ar": "الساعات", "pt": "Horas",
  "ur": "Hours", "hi": "घंटे", "bn": "ঘণ্টা"
};
NOEL_I18N["hourly.per_hour"] = {
  "en": "/hr", "es": "/h", "fr": "/h",
  "ar": "/ساعة", "pt": "/h",
  "ur": "/hr", "hi": "/घंटा", "bn": "/ঘণ্টা"
};
NOEL_I18N["hourly.miles_included"] = {
  "en": "{n} miles included per hour", "es": "{n} millas incluidas por hora",
  "fr": "{n} miles inclus par heure",
  "ar": "{n} ميل مشمول في الساعة", "pt": "{n} milhas incluídas por hora",
  "ur": "{n} miles per hour shamil hain", "hi": "प्रति घंटे {n} मील शामिल हैं", "bn": "প্রতি ঘণ্টায় {n} মাইল অন্তর্ভুক্ত"
};
NOEL_I18N["hourly.min_2"] = {
  "en": "Minimum 2 hours", "es": "Mínimo 2 horas", "fr": "Minimum 2 heures",
  "ar": "الحد الأدنى ساعتان", "pt": "Mínimo de 2 horas",
  "ur": "Minimum 2 hours", "hi": "न्यूनतम 2 घंटे", "bn": "সর্বনিম্ন ২ ঘণ্টা"
};

/* --- Keys added for the language-switcher HTML/JS wiring (2026-11-22) --- */
NOEL_I18N["chat.q_book"] = {
  "en": "How do I book?", "es": "¿Cómo reservo?", "fr": "Comment réserver ?",
  "ar": "كيف أحجز؟", "pt": "Como reservo?",
  "ur": "Ride kaise book karen?", "hi": "मैं सवारी कैसे बुक करूँ?", "bn": "আমি কীভাবে রাইড বুক করব?"
};
NOEL_I18N["chat.q_paused"] = {
  "en": "Are bookings paused?", "es": "¿Las reservas están en pausa?", "fr": "Les réservations sont-elles en pause ?",
  "ar": "هل الحجوزات متوقفة مؤقتًا؟", "pt": "As reservas estão pausadas?",
  "ur": "Kya bookings paused hain?", "hi": "क्या बुकिंग रुकी हुई हैं?", "bn": "বুকিং কি বন্ধ আছে?"
};
NOEL_I18N["chat.q_cancel"] = {
  "en": "Cancellation rules", "es": "Reglas de cancelación", "fr": "Règles d'annulation",
  "ar": "قواعد الإلغاء", "pt": "Regras de cancelamento",
  "ur": "Cancellation rules", "hi": "रद्दीकरण के नियम", "bn": "বাতিলের নিয়ম"
};
NOEL_I18N["chat.q_waiting"] = {
  "en": "Waiting time", "es": "Tiempo de espera", "fr": "Temps d'attente",
  "ar": "وقت الانتظار", "pt": "Tempo de espera",
  "ur": "Waiting time", "hi": "प्रतीक्षा समय", "bn": "অপেক্ষার সময়"
};
NOEL_I18N["chat.q_lost"] = {
  "en": "Lost item", "es": "Objeto perdido", "fr": "Objet perdu",
  "ar": "غرض مفقود", "pt": "Item perdido",
  "ur": "Khoi hui cheez", "hi": "खोई हुई चीज़", "bn": "হারানো জিনিস"
};
NOEL_I18N["chat.type_message"] = {
  "en": "Type your message…", "es": "Escribe tu mensaje…", "fr": "Écrivez votre message…",
  "ar": "اكتب رسالتك…", "pt": "Digite sua mensagem…",
  "ur": "Apna message likhen…", "hi": "अपना संदेश लिखें…", "bn": "আপনার বার্তা লিখুন…"
};
NOEL_I18N["class.back_form"] = {
  "en": "← Back to booking form", "es": "← Volver al formulario de reserva", "fr": "← Retour au formulaire de réservation",
  "ar": "← العودة إلى نموذج الحجز", "pt": "← Voltar ao formulário de reserva",
  "ur": "← Booking form par wapas", "hi": "← बुकिंग फ़ॉर्म पर वापस जाएँ", "bn": "← বুকিং ফর্মে ফিরে যান"
};
NOEL_I18N["class.cap_seating_note"] = {
  "en": "— please respect the seating capacity for safety.", "es": "— respete la capacidad de asientos por seguridad.", "fr": "— veuillez respecter la capacité d'assise pour votre sécurité.",
  "ar": "— يرجى احترام سعة المقاعد من أجل السلامة.", "pt": "— respeite a capacidade de assentos por segurança.",
  "ur": "— safety ke liye seating capacity ka khayal rakhen.", "hi": "— सुरक्षा के लिए बैठने की क्षमता का सम्मान करें।", "bn": "— নিরাপত্তার জন্য আসন ধারণক্ষমতা মেনে চলুন।"
};
NOEL_I18N["class.capacity_luggage"] = {
  "en": "Luggage", "es": "Equipaje", "fr": "Bagages",
  "ar": "الأمتعة", "pt": "Bagagem",
  "ur": "Luggage", "hi": "सामान", "bn": "লাগেজ"
};
NOEL_I18N["class.capacity_seating"] = {
  "en": "Seating", "es": "Asientos", "fr": "Places assises",
  "ar": "المقاعد", "pt": "Assentos",
  "ur": "Seating", "hi": "बैठने की जगह", "bn": "বসার জায়গা"
};
NOEL_I18N["class.choose_vehicle_class"] = {
  "en": "Choose your vehicle class", "es": "Elige la clase de vehículo", "fr": "Choisissez votre catégorie de véhicule",
  "ar": "اختر فئة السيارة", "pt": "Escolha a classe do veículo",
  "ur": "Apni vehicle class chunen", "hi": "अपनी वाहन श्रेणी चुनें", "bn": "আপনার গাড়ির শ্রেণি বেছে নিন"
};
NOEL_I18N["class.continue"] = {
  "en": "Continue", "es": "Continuar", "fr": "Continuer",
  "ar": "متابعة", "pt": "Continuar",
  "ur": "Continue", "hi": "जारी रखें", "bn": "চালিয়ে যান"
};
NOEL_I18N["class.included_meet"] = {
  "en": "Personal meet & greet", "es": "Recibimiento personal", "fr": "Accueil personnalisé",
  "ar": "استقبال شخصي", "pt": "Recepção pessoal",
  "ur": "Personal meet & greet", "hi": "व्यक्तिगत स्वागत", "bn": "ব্যক্তিগত অভ্যর্থনা"
};
NOEL_I18N["class.included_wait"] = {
  "en": "Includes up to 15 minutes of free wait time", "es": "Incluye hasta 15 minutos de espera gratis", "fr": "Jusqu'à 15 minutes d'attente gratuite incluses",
  "ar": "يشمل حتى 15 دقيقة انتظار مجاني", "pt": "Inclui até 15 minutos de espera gratuita",
  "ur": "15 minutes tak free wait time shamil hai", "hi": "15 मिनट तक का मुफ़्त प्रतीक्षा समय शामिल है", "bn": "১৫ মিনিট পর্যন্ত বিনামূল্যে অপেক্ষার সময় অন্তর্ভুক্ত"
};
NOEL_I18N["class.included_cancel"] = {
  "en": "Free to cancel up to 1 hour before pickup", "es": "Cancelación gratuita hasta 1 hora antes de la recogida", "fr": "Annulation gratuite jusqu'à 1 heure avant la prise en charge",
  "ar": "إلغاء مجاني حتى ساعة واحدة قبل موعد الاستلام", "pt": "Cancelamento gratuito até 1 hora antes da coleta",
  "ur": "Pickup se 1 hour pehle tak free cancel", "hi": "पिकअप से 1 घंटे पहले तक मुफ़्त रद्दीकरण", "bn": "পিকআপের ১ ঘণ্টা আগে পর্যন্ত বিনামূল্যে বাতিল"
};
NOEL_I18N["class.included_chargers"] = {
  "en": "iOS and Android chargers onboard", "es": "Cargadores iOS y Android a bordo", "fr": "Chargeurs iOS et Android à bord",
  "ar": "شواحن iOS وAndroid في السيارة", "pt": "Carregadores iOS e Android a bordo",
  "ur": "Gaari mein iOS aur Android chargers", "hi": "गाड़ी में iOS और Android चार्जर", "bn": "গাড়িতে iOS ও Android চার্জার"
};
NOEL_I18N["class.included_luggage"] = {
  "en": "Assistance with luggage at pickup and drop-off", "es": "Ayuda con el equipaje en la recogida y la entrega", "fr": "Aide avec les bagages à la prise en charge et à l'arrivée",
  "ar": "مساعدة في الأمتعة عند الاستلام والتوصيل", "pt": "Ajuda com a bagagem na coleta e na entrega",
  "ur": "Pickup aur drop-off par luggage mein madad", "hi": "पिकअप और ड्रॉप-ऑफ़ पर सामान में सहायता", "bn": "পিকআপ ও ড্রপ-অফে লাগেজে সাহায্য"
};
NOEL_I18N["class.name"] = {
  "en": "Your name", "es": "Tu nombre", "fr": "Votre nom",
  "ar": "اسمك", "pt": "Seu nome",
  "ur": "Aapka naam", "hi": "आपका नाम", "bn": "আপনার নাম"
};
NOEL_I18N["class.name_ph"] = {
  "en": "Full name", "es": "Nombre completo", "fr": "Nom complet",
  "ar": "الاسم الكامل", "pt": "Nome completo",
  "ur": "Poora naam", "hi": "पूरा नाम", "bn": "পুরো নাম"
};
NOEL_I18N["class.phone_ph"] = {
  "en": "Your phone number", "es": "Tu número de teléfono", "fr": "Votre numéro de téléphone",
  "ar": "رقم هاتفك", "pt": "Seu número de telefone",
  "ur": "Aapka phone number", "hi": "आपका फ़ोन नंबर", "bn": "আপনার ফোন নম্বর"
};
NOEL_I18N["class.email_ph"] = {
  "en": "you@example.com", "es": "you@example.com", "fr": "you@example.com",
  "ar": "you@example.com", "pt": "you@example.com",
  "ur": "you@example.com", "hi": "you@example.com", "bn": "you@example.com"
};
NOEL_I18N["class.note_capacity"] = {
  "en": "Guest and luggage capacities must be respected for safety reasons. If you are unsure, select a larger class.",
  "es": "Las capacidades de pasajeros y equipaje deben respetarse por seguridad. Si no está seguro, elija una clase superior.",
  "fr": "Les capacités passagers et bagages doivent être respectées pour des raisons de sécurité. En cas de doute, choisissez une catégorie supérieure.",
  "ar": "يجب احترام سعة الركاب والأمتعة لأسباب تتعلق بالسلامة. إذا كنت غير متأكد، فاختر فئة أكبر.",
  "pt": "As capacidades de passageiros e bagagem devem ser respeitadas por segurança. Se não tiver certeza, escolha uma classe maior.",
  "ur": "Safety ke liye guest aur luggage capacity ka khayal rakhen. Agar sure nahi hain, to badi class chunen.",
  "hi": "सुरक्षा कारणों से यात्री और सामान की क्षमता का सम्मान करें। यदि आप अनिश्चित हैं, तो बड़ी श्रेणी चुनें।",
  "bn": "নিরাপত্তার কারণে যাত্রী ও লাগেজের ধারণক্ষমতা মেনে চলতে হবে। নিশ্চিত না হলে বড় শ্রেণি বেছে নিন।"
};
NOEL_I18N["class.note_fare"] = {
  "en": "Your estimated total fare is based on the trip details shown above. The final fare may change if you change the pickup or drop-off location, change the vehicle type, or a different route is taken.",
  "es": "La tarifa total estimada se basa en los detalles del viaje indicados arriba. La tarifa final puede cambiar si cambia el lugar de recogida o entrega, el tipo de vehículo o si se toma otra ruta.",
  "fr": "Le tarif total estimé est basé sur les détails du trajet ci-dessus. Le tarif final peut changer si vous modifiez le lieu de prise en charge ou de dépôt, le type de véhicule ou si un autre itinéraire est suivi.",
  "ar": "الأجرة الإجمالية التقديرية مبنية على تفاصيل الرحلة أعلاه. قد تتغير الأجرة النهائية إذا غيّرت مكان الاستلام أو التوصيل أو نوع السيارة أو تم اتخاذ طريق مختلف.",
  "pt": "A tarifa total estimada baseia-se nos detalhes da viagem acima. A tarifa final pode mudar se você alterar o local de coleta ou entrega, o tipo de veículo ou se outra rota for seguida.",
  "ur": "Aapki estimated total fare upar dikhaye gaye trip details par hai. Final fare badal sakta hai agar aap pickup ya drop-off jagah, vehicle type badlen, ya koi doosra route liya jaye.",
  "hi": "आपकी अनुमानित कुल किराया ऊपर दिखाए गए यात्रा विवरण पर आधारित है। अंतिम किराया बदल सकता है यदि आप पिकअप या ड्रॉप-ऑफ़ स्थान, वाहन का प्रकार बदलते हैं, या कोई अलग मार्ग लिया जाता है।",
  "bn": "আপনার আনুমানিক মোট ভাড়া উপরে দেখানো ট্রিপের বিবরণের উপর ভিত্তি করে। পিকআপ বা ড্রপ-অফের জায়গা, গাড়ির ধরন বদলালে বা অন্য রুট নিলে চূড়ান্ত ভাড়া বদলাতে পারে।"
};
NOEL_I18N["class.note_images"] = {
  "en": "The vehicle images above are examples. You may get a different vehicle of similar quality.",
  "es": "Las imágenes de los vehículos son ejemplos. Es posible que reciba un vehículo diferente de calidad similar.",
  "fr": "Les images des véhicules ci-dessus sont des exemples. Vous pouvez recevoir un véhicule différent de qualité similaire.",
  "ar": "صور السيارات أعلاه أمثلة فقط. قد تحصل على سيارة مختلفة بجودة مماثلة.",
  "pt": "As imagens dos veículos acima são exemplos. Você pode receber um veículo diferente de qualidade semelhante.",
  "ur": "Upar dikhayi gayi gaariyon ki photos sirf examples hain. Aapko same quality ki koi doosri gaari mil sakti hai.",
  "hi": "ऊपर दिखाई गई वाहन की तस्वीरें उदाहरण हैं। आपको समान गुणवत्ता का कोई अलग वाहन मिल सकता है।",
  "bn": "উপরের গাড়ির ছবিগুলো উদাহরণ মাত্র। আপনি একই মানের অন্য গাড়ি পেতে পারেন।"
};
NOEL_I18N["class.price_breakdown"] = {
  "en": "Price breakdown", "es": "Desglose del precio", "fr": "Détail du prix",
  "ar": "تفصيل السعر", "pt": "Detalhamento do preço",
  "ur": "Price breakdown", "hi": "कीमत का विवरण", "bn": "মূল্যের বিবরণ"
};
NOEL_I18N["class.select_business_class"] = {
  "en": "Select Business Class", "es": "Seleccionar Business Class", "fr": "Sélectionner Business Class",
  "ar": "اختر Business Class", "pt": "Selecionar Business Class",
  "ur": "Business Class select karen", "hi": "Business Class चुनें", "bn": "Business Class বেছে নিন"
};
NOEL_I18N["form.flight"] = {
  "en": "Flight number", "es": "Número de vuelo", "fr": "Numéro de vol",
  "ar": "رقم الرحلة", "pt": "Número do voo",
  "ur": "Flight number", "hi": "उड़ान संख्या", "bn": "ফ্লাইট নম্বর"
};
NOEL_I18N["form.phone"] = {
  "en": "Phone number", "es": "Número de teléfono", "fr": "Numéro de téléphone",
  "ar": "رقم الهاتف", "pt": "Número de telefone",
  "ur": "Phone number", "hi": "फ़ोन नंबर", "bn": "ফোন নম্বর"
};
NOEL_I18N["form.time"] = {
  "en": "Pickup time", "es": "Hora de recogida", "fr": "Heure de prise en charge",
  "ar": "وقت الاستلام", "pt": "Hora da coleta",
  "ur": "Pickup time", "hi": "पिकअप का समय", "bn": "পিকআপের সময়"
};
NOEL_I18N["status.card_cvc"] = {
  "en": "CVC", "es": "CVC", "fr": "CVC",
  "ar": "CVC", "pt": "CVC",
  "ur": "CVC", "hi": "CVC", "bn": "CVC"
};
NOEL_I18N["status.card_expiry"] = {
  "en": "Expiry (MM/YY)", "es": "Caducidad (MM/AA)", "fr": "Expiration (MM/AA)",
  "ar": "تاريخ الانتهاء (شهر/سنة)", "pt": "Validade (MM/AA)",
  "ur": "Expiry (MM/YY)", "hi": "समाप्ति (MM/YY)", "bn": "মেয়াদ (MM/YY)"
};
NOEL_I18N["status.language_label"] = {
  "en": "Language:", "es": "Idioma:", "fr": "Langue :",
  "ar": "اللغة:", "pt": "Idioma:",
  "ur": "Language:", "hi": "भाषा:", "bn": "ভাষা:"
};
NOEL_I18N["status.on_way"] = {
  "en": "Your chauffeur is on the way.", "es": "Tu chófer está en camino.", "fr": "Votre chauffeur est en route.",
  "ar": "سائقك في الطريق إليك.", "pt": "Seu motorista está a caminho.",
  "ur": "Aapka chauffeur raste mein hai.", "hi": "आपका चालक रास्ते में है।", "bn": "আপনার চালক পথে আছেন।"
};
NOEL_I18N["status.on_way_title"] = {
  "en": "Your chauffeur on the way", "es": "Tu chófer en camino", "fr": "Votre chauffeur en route",
  "ar": "سائقك في الطريق", "pt": "Seu motorista a caminho",
  "ur": "Aapka chauffeur raste mein", "hi": "आपका चालक रास्ते में", "bn": "আপনার চালক পথে"
};
NOEL_I18N["status.pay"] = {
  "en": "Pay", "es": "Pagar", "fr": "Payer",
  "ar": "ادفع", "pt": "Pagar",
  "ur": "Pay karen", "hi": "भुगतान करें", "bn": "পে করুন"
};
NOEL_I18N["status.pay_unavailable"] = {
  "en": "Card payments are not set up yet. Please try again later.",
  "es": "Los pagos con tarjeta aún no están configurados. Inténtalo de nuevo más tarde.",
  "fr": "Les paiements par carte ne sont pas encore configurés. Veuillez réessayer plus tard.",
  "ar": "الدفع بالبطاقة غير مُعد بعد. يرجى المحاولة مرة أخرى لاحقًا.",
  "pt": "Os pagamentos com cartão ainda não estão configurados. Tente novamente mais tarde.",
  "ur": "Card payments abhi set up nahi hain. Please baad mein phir try karen.",
  "hi": "कार्ड भुगतान अभी सेट नहीं है। कृपया बाद में पुनः प्रयास करें।",
  "bn": "কার্ড পেমেন্ট এখনো সেট আপ হয়নি। পরে আবার চেষ্টা করুন।"
};
NOEL_I18N["status.single_total"] = {
  "en": "One single total for your ride. No breakdown, no hidden charges.",
  "es": "Un solo total para tu viaje. Sin desglose, sin cargos ocultos.",
  "fr": "Un seul total pour votre trajet. Aucun détail, aucun frais caché.",
  "ar": "إجمالي واحد لرحلتك. لا تفصيل ولا رسوم خفية.",
  "pt": "Um único total para sua viagem. Sem detalhamento, sem taxas ocultas.",
  "ur": "Aapki ride ke liye ek hi total. Koi breakdown nahi, koi hidden charges nahi.",
  "hi": "आपकी सवारी के लिए एक ही कुल राशि। कोई विवरण नहीं, कोई छिपा शुल्क नहीं।",
  "bn": "আপনার রাইডের জন্য একটাই মোট। কোনো বিবরণ নেই, কোনো লুকানো চার্জ নেই।"
};
NOEL_I18N["status.stripe_note"] = {
  "en": "Your card is charged as a hold when you book. Your card details go directly to Stripe — they are never typed into, or stored on, this site.",
  "es": "Tu tarjeta se carga como retención al reservar. Los datos de tu tarjeta van directamente a Stripe: nunca se escriben ni se guardan en este sitio.",
  "fr": "Votre carte est débitée à titre de garantie lors de la réservation. Les coordonnées de votre carte vont directement à Stripe — elles ne sont jamais saisies ni stockées sur ce site.",
  "ar": "يتم خصم بطاقتك كحجز مؤقت عند الحجز. تذهب بيانات بطاقتك مباشرة إلى Stripe — ولا تُكتب أو تُخزَّن أبدًا على هذا الموقع.",
  "pt": "Seu cartão é cobrado como retenção ao reservar. Os dados do cartão vão diretamente para a Stripe — nunca são digitados nem armazenados neste site.",
  "ur": "Book karte waqt aapke card par hold lagaya jata hai. Aapke card ki details seedha Stripe ko jati hain — ye is site par kabhi type ya save nahi hoti.",
  "hi": "बुक करते समय आपके कार्ड पर होल्ड लगाया जाता है। आपके कार्ड का विवरण सीधे Stripe को जाता है — यह इस साइट पर कभी टाइप या संग्रहीत नहीं होता।",
  "bn": "বুক করার সময় আপনার কার্ডে হোল্ড চার্জ করা হয়। আপনার কার্ডের বিবরণ সরাসরি Stripe-এ যায় — এটি এই সাইটে কখনো টাইপ বা সংরক্ষণ করা হয় না।"
};
NOEL_I18N["status.thankyou_test"] = {
  "en": "Test mode — no real charge. This booking was paid in test mode; no real payment was taken.",
  "es": "Modo de prueba: sin cargo real. Esta reserva se pagó en modo de prueba; no se realizó ningún pago real.",
  "fr": "Mode test — aucun débit réel. Cette réservation a été payée en mode test ; aucun paiement réel n'a été effectué.",
  "ar": "وضع الاختبار — لا يوجد خصم حقيقي. تم دفع هذا الحجز في وضع الاختبار؛ ولم يتم أخذ أي دفعة حقيقية.",
  "pt": "Modo de teste — sem cobrança real. Esta reserva foi paga em modo de teste; nenhum pagamento real foi feito.",
  "ur": "Test mode — koi real charge nahi. Ye booking test mode mein pay ki gayi thi; koi real payment nahi li gayi.",
  "hi": "परीक्षण मोड — कोई वास्तविक शुल्क नहीं। यह बुकिंग परीक्षण मोड में भुगतान की गई थी; कोई वास्तविक भुगतान नहीं लिया गया।",
  "bn": "টেস্ট মোড — কোনো আসল চার্জ নেই। এই বুকিং টেস্ট মোডে পে করা হয়েছিল; কোনো আসল পেমেন্ট নেওয়া হয়নি।"
};
NOEL_I18N["status.waiting_charge"] = {
  "en": "Waiting charge", "es": "Cargo por espera", "fr": "Frais d'attente",
  "ar": "رسوم الانتظار", "pt": "Taxa de espera",
  "ur": "Waiting charge", "hi": "प्रतीक्षा शुल्क", "bn": "অপেক্ষার চার্জ"
};
NOEL_I18N["class.hourly_miles_note"] = {
  "en": "Includes {miles} miles of travel ({mph} miles per hour) — taxes and tolls included.",
  "es": "Incluye {miles} millas de viaje ({mph} millas por hora); impuestos y peajes incluidos.",
  "fr": "Comprend {miles} miles de trajet ({mph} miles par heure) — taxes et péages inclus.",
  "ar": "يشمل {miles} ميلًا من السفر ({mph} ميلًا في الساعة) — الضرائب والرسوم مشمولة.",
  "pt": "Inclui {miles} milhas de viagem ({mph} milhas por hora) — impostos e pedágios incluídos.",
  "ur": "{miles} miles ka safar shamil hai ({mph} miles per hour) — taxes aur tolls shamil hain.",
  "hi": "{miles} मील की यात्रा शामिल है ({mph} मील प्रति घंटा) — कर और टोल शामिल हैं।",
  "bn": "{miles} মাইল ভ্রমণ অন্তর্ভুক্ত ({mph} মাইল প্রতি ঘণ্টা) — ট্যাক্স ও টোল অন্তর্ভুক্ত।"
};
NOEL_I18N["class.select_class"] = {
  "en": "Select {label}", "es": "Seleccionar {label}", "fr": "Sélectionner {label}",
  "ar": "اختر {label}", "pt": "Selecionar {label}",
  "ur": "{label} select karen", "hi": "{label} चुनें", "bn": "{label} বেছে নিন"
};
NOEL_I18N["class.hour_suffix"] = {
  "en": " hour(s)", "es": " hora(s)", "fr": " heure(s)",
  "ar": " ساعة", "pt": " hora(s)",
  "ur": " hour(s)", "hi": " घंटा", "bn": " ঘণ্টা"
};
NOEL_I18N["status.return_trip_label"] = {
  "en": "Return trip", "es": "Viaje de regreso", "fr": "Trajet retour",
  "ar": "رحلة العودة", "pt": "Viagem de volta",
  "ur": "Return trip", "hi": "वापसी यात्रा", "bn": "ফেরার ট্রিপ"
};
NOEL_I18N["status.one_way_label"] = {
  "en": "One way", "es": "Solo ida", "fr": "Aller simple",
  "ar": "ذهاب فقط", "pt": "Somente ida",
  "ur": "One way", "hi": "एक तरफ़ा", "bn": "ওয়ান ওয়ে"
};
NOEL_I18N["status.awaiting_payment"] = {
  "en": "Payment needed to confirm your ride", "es": "Pago necesario para confirmar tu viaje", "fr": "Paiement requis pour confirmer votre trajet",
  "ar": "يلزم الدفع لتأكيد رحلتك", "pt": "Pagamento necessário para confirmar sua viagem",
  "ur": "Aapki ride confirm karne ke liye payment zaroori hai", "hi": "आपकी सवारी की पुष्टि के लिए भुगतान आवश्यक है", "bn": "আপনার রাইড নিশ্চিত করতে পেমেন্ট প্রয়োজন"
};
NOEL_I18N["status.offered"] = {
  "en": "Finding your chauffeur…", "es": "Buscando tu chófer…", "fr": "Recherche de votre chauffeur…",
  "ar": "جارٍ البحث عن سائقك…", "pt": "Procurando seu motorista…",
  "ur": "Aapka chauffeur dhoondha ja raha hai…", "hi": "आपका चालक खोजा जा रहा है…", "bn": "আপনার চালক খোঁজা হচ্ছে…"
};
NOEL_I18N["status.accepted"] = {
  "en": "Chauffeur confirmed", "es": "Chófer confirmado", "fr": "Chauffeur confirmé",
  "ar": "تم تأكيد السائق", "pt": "Motorista confirmado",
  "ur": "Chauffeur confirmed", "hi": "चालक की पुष्टि हो गई", "bn": "চালক নিশ্চিত হয়েছে"
};
NOEL_I18N["status.en_route"] = {
  "en": "Your chauffeur is on the way", "es": "Tu chófer está en camino", "fr": "Votre chauffeur est en route",
  "ar": "سائقك في الطريق", "pt": "Seu motorista está a caminho",
  "ur": "Aapka chauffeur raste mein hai", "hi": "आपका चालक रास्ते में है", "bn": "আপনার চালক পথে আছেন"
};
NOEL_I18N["status.started"] = {
  "en": "Your ride is under way", "es": "Tu viaje está en curso", "fr": "Votre trajet est en cours",
  "ar": "رحلتك جارية", "pt": "Sua viagem está em andamento",
  "ur": "Aapki ride chal rahi hai", "hi": "आपकी सवारी चल रही है", "bn": "আপনার রাইড চলছে"
};
NOEL_I18N["status.on_trip"] = {
  "en": "Your ride is under way", "es": "Tu viaje está en curso", "fr": "Votre trajet est en cours",
  "ar": "رحلتك جارية", "pt": "Sua viagem está em andamento",
  "ur": "Aapki ride chal rahi hai", "hi": "आपकी सवारी चल रही है", "bn": "আপনার রাইড চলছে"
};
NOEL_I18N["status.in_progress"] = {
  "en": "Your ride is under way", "es": "Tu viaje está en curso", "fr": "Votre trajet est en cours",
  "ar": "رحلتك جارية", "pt": "Sua viagem está em andamento",
  "ur": "Aapki ride chal rahi hai", "hi": "आपकी सवारी चल रही है", "bn": "আপনার রাইড চলছে"
};
NOEL_I18N["status.completed"] = {
  "en": "Ride completed — thank you", "es": "Viaje completado — gracias", "fr": "Trajet terminé — merci",
  "ar": "اكتملت الرحلة — شكرًا", "pt": "Viagem concluída — obrigado",
  "ur": "Ride complete — shukriya", "hi": "सवारी पूरी हो गई — धन्यवाद", "bn": "রাইড সম্পন্ন হয়েছে — ধন্যবাদ"
};
NOEL_I18N["status.cancelled"] = {
  "en": "This booking was cancelled", "es": "Esta reserva fue cancelada", "fr": "Cette réservation a été annulée",
  "ar": "تم إلغاء هذا الحجز", "pt": "Esta reserva foi cancelada",
  "ur": "Ye booking cancel ho gayi thi", "hi": "यह बुकिंग रद्द कर दी गई थी", "bn": "এই বুকিং বাতিল করা হয়েছিল"
};
NOEL_I18N["class.explore_class"] = {
  "en": "Explore {label} details", "es": "Explorar los detalles de {label}", "fr": "Explorer les détails de {label}",
  "ar": "استكشف تفاصيل {label}", "pt": "Explorar detalhes de {label}",
  "ur": "{label} ki details dekhen", "hi": "{label} का विवरण देखें", "bn": "{label}-এর বিবরণ দেখুন"
};
NOEL_I18N["class.carry_on"] = {
  "en": "{n} x Carry-on", "es": "{n} x equipaje de mano", "fr": "{n} x bagage cabine",
  "ar": "{n} × حقيبة يد", "pt": "{n} x bagagem de mão",
  "ur": "{n} x Carry-on", "hi": "{n} x केबिन बैग", "bn": "{n} x ক্যারি-অন"
};
NOEL_I18N["class.passengers_count"] = {
  "en": "{n} passengers", "es": "{n} pasajeros", "fr": "{n} passagers",
  "ar": "{n} ركاب", "pt": "{n} passageiros",
  "ur": "{n} passengers", "hi": "{n} यात्री", "bn": "{n} জন যাত্রী"
};
NOEL_I18N["class.highlight_n"] = {
  "en": "Highlight {n}", "es": "Aspecto {n}", "fr": "Point fort {n}",
  "ar": "الميزة {n}", "pt": "Destaque {n}",
  "ur": "Highlight {n}", "hi": "विशेषता {n}", "bn": "হাইলাইট {n}"
};
NOEL_I18N["class.referral_discount_row"] = {
  "en": "Referral discount", "es": "Descuento por recomendación", "fr": "Remise de parrainage",
  "ar": "خصم الإحالة", "pt": "Desconto por indicação",
  "ur": "Referral discount", "hi": "रेफ़रल छूट", "bn": "রেফারেল ছাড়"
};
NOEL_I18N["form.paused_msg"] = {
  "en": "Bookings are paused while we update our prices. Please check back soon.",
  "es": "Las reservas están en pausa mientras actualizamos los precios. Vuelve a intentarlo pronto.",
  "fr": "Les réservations sont en pause pendant la mise à jour de nos prix. Veuillez revenir bientôt.",
  "ar": "الحجوزات متوقفة مؤقتًا أثناء تحديث أسعارنا. يرجى العودة قريبًا.",
  "pt": "As reservas estão pausadas enquanto atualizamos os preços. Volte em breve.",
  "ur": "Prices update karte waqt bookings paused hain. Please thodi der mein phir check karen.",
  "hi": "हमारी कीमतें अपडेट करते समय बुकिंग रुकी हुई है। कृपया जल्द ही फिर से देखें।",
  "bn": "আমরা দাম আপডেট করার সময় বুকিং বন্ধ আছে। শীঘ্রই আবার দেখুন।"
};
NOEL_I18N["form.hourly_hours_error"] = {
  "en": "Hourly bookings need 2 to 24 hours.", "es": "Las reservas por horas necesitan de 2 a 24 horas.", "fr": "Les réservations à l'heure nécessitent de 2 à 24 heures.",
  "ar": "الحجوزات بالساعة تحتاج من ساعتين إلى 24 ساعة.", "pt": "Reservas por hora precisam de 2 a 24 horas.",
  "ur": "Hourly bookings ke liye 2 se 24 hours chahiye.", "hi": "प्रति घंटा बुकिंग के लिए 2 से 24 घंटे चाहिए।", "bn": "ঘণ্টাভিত্তিক বুকিংয়ের জন্য ২ থেকে ২৪ ঘণ্টা প্রয়োজন।"
};
NOEL_I18N["form.choose_date_time"] = {
  "en": "Please choose a date and time.", "es": "Elige una fecha y una hora.", "fr": "Veuillez choisir une date et une heure.",
  "ar": "يرجى اختيار تاريخ ووقت.", "pt": "Escolha uma data e hora.",
  "ur": "Please date aur time chunen.", "hi": "कृपया तारीख़ और समय चुनें।", "bn": "একটি তারিখ ও সময় বেছে নিন।"
};
NOEL_I18N["class.fill_details"] = {
  "en": "Please fill in your name, phone and email.", "es": "Completa tu nombre, teléfono y correo electrónico.", "fr": "Veuillez renseigner votre nom, votre téléphone et votre e-mail.",
  "ar": "يرجى إدخال اسمك ورقم هاتفك وبريدك الإلكتروني.", "pt": "Preencha seu nome, telefone e e-mail.",
  "ur": "Please apna naam, phone aur email likhen.", "hi": "कृपया अपना नाम, फ़ोन और ईमेल लिखें।", "bn": "আপনার নাম, ফোন ও ইমেইল লিখুন।"
};
NOEL_I18N["form.flight_title_optional"] = {
  "en": "Add your flight number (optional)", "es": "Añade tu número de vuelo (opcional)", "fr": "Ajoutez votre numéro de vol (facultatif)",
  "ar": "أضف رقم رحلتك (اختياري)", "pt": "Adicione seu número de voo (opcional)",
  "ur": "Apna flight number likhen (optional)", "hi": "अपनी उड़ान संख्या जोड़ें (वैकल्पिक)", "bn": "আপনার ফ্লাইট নম্বর যোগ করুন (ঐচ্ছিক)"
};
NOEL_I18N["class.details_save_failed"] = {
  "en": "Your details could not be saved. Please try again.", "es": "No se pudieron guardar tus datos. Inténtalo de nuevo.", "fr": "Vos coordonnées n'ont pas pu être enregistrées. Veuillez réessayer.",
  "ar": "تعذّر حفظ بياناتك. يرجى المحاولة مرة أخرى.", "pt": "Seus dados não puderam ser salvos. Tente novamente.",
  "ur": "Aapki details save nahi ho saki. Please phir try karen.", "hi": "आपका विवरण सहेजा नहीं जा सका। कृपया पुनः प्रयास करें।", "bn": "আপনার বিবরণ সংরক্ষণ করা যায়নি। আবার চেষ্টা করুন।"
};
NOEL_I18N["form.something_wrong"] = {
  "en": "Something went wrong. Please try again.", "es": "Algo salió mal. Inténtalo de nuevo.", "fr": "Quelque chose s'est mal passé. Veuillez réessayer.",
  "ar": "حدث خطأ ما. يرجى المحاولة مرة أخرى.", "pt": "Algo deu errado. Tente novamente.",
  "ur": "Kuch ghalat ho gaya. Please phir try karen.", "hi": "कुछ ग़लत हो गया। कृपया पुनः प्रयास करें।", "bn": "কিছু ভুল হয়েছে। আবার চেষ্টা করুন।"
};
NOEL_I18N["status.chat_empty"] = {
  "en": "No messages yet. Your chauffeur can read your messages here.",
  "es": "Aún no hay mensajes. Tu chófer puede leer tus mensajes aquí.",
  "fr": "Aucun message pour l'instant. Votre chauffeur peut lire vos messages ici.",
  "ar": "لا توجد رسائل بعد. يمكن لسائقك قراءة رسائلك هنا.",
  "pt": "Ainda não há mensagens. Seu motorista pode ler suas mensagens aqui.",
  "ur": "Abhi koi messages nahi hain. Aapka chauffeur aapke messages yahan padh sakta hai.",
  "hi": "अभी तक कोई संदेश नहीं है। आपका चालक आपके संदेश यहाँ पढ़ सकता है।",
  "bn": "এখনো কোনো বার্তা নেই। আপনার চালক আপনার বার্তা এখানে পড়তে পারবেন।"
};
NOEL_I18N["status.you"] = {
  "en": "You", "es": "Tú", "fr": "Vous",
  "ar": "أنت", "pt": "Você",
  "ur": "Aap", "hi": "आप", "bn": "আপনি"
};
NOEL_I18N["status.chauffeur_word"] = {
  "en": "Chauffeur", "es": "Chófer", "fr": "Chauffeur",
  "ar": "السائق", "pt": "Motorista",
  "ur": "Chauffeur", "hi": "चालक", "bn": "চালক"
};
NOEL_I18N["status.pay_start_failed"] = {
  "en": "Could not start the secure payment form. Please try again.",
  "es": "No se pudo iniciar el formulario de pago seguro. Inténtalo de nuevo.",
  "fr": "Impossible de démarrer le formulaire de paiement sécurisé. Veuillez réessayer.",
  "ar": "تعذّر بدء نموذج الدفع الآمن. يرجى المحاولة مرة أخرى.",
  "pt": "Não foi possível iniciar o formulário de pagamento seguro. Tente novamente.",
  "ur": "Secure payment form start nahi ho saka. Please phir try karen.",
  "hi": "सुरक्षित भुगतान फ़ॉर्म शुरू नहीं हो सका। कृपया पुनः प्रयास करें।",
  "bn": "নিরাপদ পেমেন্ট ফর্ম শুরু করা যায়নি। আবার চেষ্টা করুন।"
};
NOEL_I18N["status.remove"] = {
  "en": "Remove", "es": "Eliminar", "fr": "Supprimer",
  "ar": "إزالة", "pt": "Remover",
  "ur": "Remove", "hi": "हटाएँ", "bn": "সরান"
};
NOEL_I18N["status.remove_card_confirm"] = {
  "en": "Remove this saved card?", "es": "¿Eliminar esta tarjeta guardada?", "fr": "Supprimer cette carte enregistrée ?",
  "ar": "إزالة هذه البطاقة المحفوظة؟", "pt": "Remover este cartão salvo?",
  "ur": "Ye saved card remove kar den?", "hi": "क्या यह सहेजा गया कार्ड हटाएँ?", "bn": "এই সংরক্ষিত কার্ডটি সরাবেন?"
};
NOEL_I18N["status.remove_card_failed"] = {
  "en": "That card could not be removed.", "es": "No se pudo eliminar esa tarjeta.", "fr": "Cette carte n'a pas pu être supprimée.",
  "ar": "تعذّرت إزالة هذه البطاقة.", "pt": "Não foi possível remover esse cartão.",
  "ur": "Wo card remove nahi ho saka.", "hi": "वह कार्ड हटाया नहीं जा सका।", "bn": "ওই কার্ড সরানো যায়নি।"
};
NOEL_I18N["status.pay_confirm_missing"] = {
  "en": "Payment needs confirmation, but no confirmation was provided. Please try again.",
  "es": "El pago necesita confirmación, pero no se proporcionó ninguna. Inténtalo de nuevo.",
  "fr": "Le paiement nécessite une confirmation, mais aucune n'a été fournie. Veuillez réessayer.",
  "ar": "الدفع يحتاج إلى تأكيد، لكن لم يتم تقديم أي تأكيد. يرجى المحاولة مرة أخرى.",
  "pt": "O pagamento precisa de confirmação, mas nenhuma foi fornecida. Tente novamente.",
  "ur": "Payment ke liye confirmation chahiye, lekin koi confirmation nahi mili. Please phir try karen.",
  "hi": "भुगतान के लिए पुष्टि आवश्यक है, लेकिन कोई पुष्टि नहीं मिली। कृपया पुनः प्रयास करें।",
  "bn": "পেমেন্টের জন্য নিশ্চিতকরণ প্রয়োজন, কিন্তু কোনো নিশ্চিতকরণ দেওয়া হয়নি। আবার চেষ্টা করুন।"
};
NOEL_I18N["status.confirming"] = {
  "en": "Confirming…", "es": "Confirmando…", "fr": "Confirmation…",
  "ar": "جارٍ التأكيد…", "pt": "Confirmando…",
  "ur": "Confirm ho raha hai…", "hi": "पुष्टि हो रही है…", "bn": "নিশ্চিত করা হচ্ছে…"
};
NOEL_I18N["status.card_confirm_failed"] = {
  "en": "Your card could not be confirmed. Please try again.", "es": "No se pudo confirmar tu tarjeta. Inténtalo de nuevo.", "fr": "Votre carte n'a pas pu être confirmée. Veuillez réessayer.",
  "ar": "تعذّر تأكيد بطاقتك. يرجى المحاولة مرة أخرى.", "pt": "Seu cartão não pôde ser confirmado. Tente novamente.",
  "ur": "Aapka card confirm nahi ho saka. Please phir try karen.", "hi": "आपका कार्ड पुष्ट नहीं हो सका। कृपया पुनः प्रयास करें।", "bn": "আপনার কার্ড নিশ্চিত করা যায়নি। আবার চেষ্টা করুন।"
};
NOEL_I18N["status.processing"] = {
  "en": "Processing…", "es": "Procesando…", "fr": "Traitement…",
  "ar": "جارٍ المعالجة…", "pt": "Processando…",
  "ur": "Processing…", "hi": "प्रक्रिया चल रही है…", "bn": "প্রক্রিয়া চলছে…"
};
NOEL_I18N["status.processing_test"] = {
  "en": "Processing (test mode)…", "es": "Procesando (modo de prueba)…", "fr": "Traitement (mode test)…",
  "ar": "جارٍ المعالجة (وضع الاختبار)…", "pt": "Processando (modo de teste)…",
  "ur": "Processing (test mode)…", "hi": "प्रक्रिया चल रही है (परीक्षण मोड)…", "bn": "প্রক্রিয়া চলছে (টেস্ট মোড)…"
};
NOEL_I18N["status.pay_failed"] = {
  "en": "Payment could not be completed. Please try again.", "es": "No se pudo completar el pago. Inténtalo de nuevo.", "fr": "Le paiement n'a pas pu être effectué. Veuillez réessayer.",
  "ar": "تعذّر إتمام الدفع. يرجى المحاولة مرة أخرى.", "pt": "O pagamento não pôde ser concluído. Tente novamente.",
  "ur": "Payment complete nahi ho saka. Please phir try karen.", "hi": "भुगतान पूरा नहीं हो सका। कृपया पुनः प्रयास करें।", "bn": "পেমেন্ট সম্পন্ন করা যায়নি। আবার চেষ্টা করুন।"
};
NOEL_I18N["status.pay_loading_wait"] = {
  "en": "The secure payment form is still loading. Please wait a moment and try again.",
  "es": "El formulario de pago seguro aún se está cargando. Espera un momento e inténtalo de nuevo.",
  "fr": "Le formulaire de paiement sécurisé est encore en cours de chargement. Veuillez patienter un instant et réessayer.",
  "ar": "نموذج الدفع الآمن ما زال يُحمَّل. يرجى الانتظار لحظة ثم المحاولة مرة أخرى.",
  "pt": "O formulário de pagamento seguro ainda está carregando. Aguarde um momento e tente novamente.",
  "ur": "Secure payment form abhi load ho raha hai. Please thoda wait karke phir try karen.",
  "hi": "सुरक्षित भुगतान फ़ॉर्म अभी भी लोड हो रहा है। कृपया थोड़ा प्रतीक्षा करें और पुनः प्रयास करें।",
  "bn": "নিরাপদ পেমেন্ট ফর্ম এখনো লোড হচ্ছে। একটু অপেক্ষা করে আবার চেষ্টা করুন।"
};
NOEL_I18N["status.check_card"] = {
  "en": "Please check your card details and try again.", "es": "Revisa los datos de tu tarjeta e inténtalo de nuevo.", "fr": "Veuillez vérifier les coordonnées de votre carte et réessayer.",
  "ar": "يرجى التحقق من بيانات بطاقتك والمحاولة مرة أخرى.", "pt": "Verifique os dados do cartão e tente novamente.",
  "ur": "Please apne card ki details check karke phir try karen.", "hi": "कृपया अपने कार्ड का विवरण जाँचें और पुनः प्रयास करें।", "bn": "আপনার কার্ডের বিবরণ দেখে আবার চেষ্টা করুন।"
};
NOEL_I18N["status.cancel_failed"] = {
  "en": "Cancellation could not be completed.", "es": "No se pudo completar la cancelación.", "fr": "L'annulation n'a pas pu être effectuée.",
  "ar": "تعذّر إتمام الإلغاء.", "pt": "O cancelamento não pôde ser concluído.",
  "ur": "Cancellation complete nahi ho saki.", "hi": "रद्दीकरण पूरा नहीं हो सका।", "bn": "বাতিল সম্পন্ন করা যায়নি।"
};
NOEL_I18N["status.pickup_prefix"] = {
  "en": " · Pickup: ", "es": " · Recogida: ", "fr": " · Prise en charge : ",
  "ar": " · الاستلام: ", "pt": " · Coleta: ",
  "ur": " · Pickup: ", "hi": " · पिकअप: ", "bn": " · পিকআপ: "
};
NOEL_I18N["status.reach_booking"] = {
  "en": "Could not reach the booking service. Please try again.",
  "es": "No se pudo contactar con el servicio de reservas. Inténtalo de nuevo.",
  "fr": "Impossible de joindre le service de réservation. Veuillez réessayer.",
  "ar": "تعذّر الوصول إلى خدمة الحجز. يرجى المحاولة مرة أخرى.",
  "pt": "Não foi possível acessar o serviço de reservas. Tente novamente.",
  "ur": "Booking service se connect nahi ho saka. Please phir try karen.",
  "hi": "बुकिंग सेवा से संपर्क नहीं हो सका। कृपया पुनः प्रयास करें।",
  "bn": "বুকিং পরিষেবায় পৌঁছানো যায়নি। আবার চেষ্টা করুন।"
};
NOEL_I18N["status.reach_payment"] = {
  "en": "Could not reach the payment service. Please try again.",
  "es": "No se pudo contactar con el servicio de pago. Inténtalo de nuevo.",
  "fr": "Impossible de joindre le service de paiement. Veuillez réessayer.",
  "ar": "تعذّر الوصول إلى خدمة الدفع. يرجى المحاولة مرة أخرى.",
  "pt": "Não foi possível acessar o serviço de pagamento. Tente novamente.",
  "ur": "Payment service se connect nahi ho saka. Please phir try karen.",
  "hi": "भुगतान सेवा से संपर्क नहीं हो सका। कृपया पुनः प्रयास करें।",
  "bn": "পেমেন্ট পরিষেবায় পৌঁছানো যায়নি। আবার চেষ্টা করুন।"
};
NOEL_I18N["status.reach_payment_check"] = {
  "en": "Could not reach the payment service. Please check your connection and try again.",
  "es": "No se pudo contactar con el servicio de pago. Revisa tu conexión e inténtalo de nuevo.",
  "fr": "Impossible de joindre le service de paiement. Veuillez vérifier votre connexion et réessayer.",
  "ar": "تعذّر الوصول إلى خدمة الدفع. يرجى التحقق من اتصالك والمحاولة مرة أخرى.",
  "pt": "Não foi possível acessar o serviço de pagamento. Verifique sua conexão e tente novamente.",
  "ur": "Payment service se connect nahi ho saka. Please apna connection check karke phir try karen.",
  "hi": "भुगतान सेवा से संपर्क नहीं हो सका। कृपया अपना कनेक्शन जाँचें और पुनः प्रयास करें।",
  "bn": "পেমেন্ট পরিষেবায় পৌঁছানো যায়নি। আপনার সংযোগ দেখে আবার চেষ্টা করুন।"
};
NOEL_I18N["status.view_ride"] = {
  "en": "View this ride", "es": "Ver este viaje", "fr": "Voir ce trajet",
  "ar": "عرض هذه الرحلة", "pt": "Ver esta viagem",
  "ur": "Ye ride dekhen", "hi": "यह सवारी देखें", "bn": "এই রাইড দেখুন"
};
NOEL_I18N["status.lookup_failed_email"] = {
  "en": "Could not look up rides for that email.", "es": "No se pudieron buscar viajes para ese correo.", "fr": "Impossible de rechercher des trajets pour cet e-mail.",
  "ar": "تعذّر البحث عن رحلات لهذا البريد الإلكتروني.", "pt": "Não foi possível buscar viagens para esse e-mail.",
  "ur": "Is email ke liye rides nahi mil saki.", "hi": "उस ईमेल के लिए सवारियाँ नहीं मिल सकीं।", "bn": "ওই ইমেইলের জন্য রাইড খুঁজে পাওয়া যায়নি।"
};
NOEL_I18N["status.flight_prefix"] = {
  "en": "Flight: ", "es": "Vuelo: ", "fr": "Vol : ",
  "ar": "الرحلة: ", "pt": "Voo: ",
  "ur": "Flight: ", "hi": "उड़ान: ", "bn": "ফ্লাইট: "
};
NOEL_I18N["status.chauffeur_prefix"] = {
  "en": "Chauffeur: ", "es": "Chófer: ", "fr": "Chauffeur : ",
  "ar": "السائق: ", "pt": "Motorista: ",
  "ur": "Chauffeur: ", "hi": "चालक: ", "bn": "চালক: "
};
NOEL_I18N["form.prev_month"] = {
  "en": "Previous month", "es": "Mes anterior", "fr": "Mois précédent",
  "ar": "الشهر السابق", "pt": "Mês anterior",
  "ur": "Pichla month", "hi": "पिछला महीना", "bn": "আগের মাস"
};
NOEL_I18N["form.next_month"] = {
  "en": "Next month", "es": "Mes siguiente", "fr": "Mois suivant",
  "ar": "الشهر التالي", "pt": "Próximo mês",
  "ur": "Agla month", "hi": "अगला महीना", "bn": "পরের মাস"
};
NOEL_I18N["status.your_pickup_point"] = {
  "en": "your pickup point", "es": "tu punto de recogida", "fr": "votre point de prise en charge",
  "ar": "نقطة الاستلام الخاصة بك", "pt": "seu ponto de coleta",
  "ur": "aapka pickup point", "hi": "आपका पिकअप पॉइंट", "bn": "আপনার পিকআপ পয়েন্ট"
};
NOEL_I18N["status.cancel_confirm_app"] = {
  "en": "Cancel this booking? The cancellation rules apply.",
  "es": "¿Cancelar esta reserva? Se aplican las reglas de cancelación.",
  "fr": "Annuler cette réservation ? Les règles d'annulation s'appliquent.",
  "ar": "إلغاء هذا الحجز؟ تنطبق قواعد الإلغاء.",
  "pt": "Cancelar esta reserva? As regras de cancelamento se aplicam.",
  "ur": "Ye booking cancel kar den? Cancellation rules apply honge.",
  "hi": "क्या यह बुकिंग रद्द करें? रद्दीकरण के नियम लागू होंगे।",
  "bn": "এই বুকিং বাতিল করবেন? বাতিলের নিয়ম প্রযোজ্য হবে।"
};
NOEL_I18N["class.hl0_caption"] = {
  "en": "Clean, quiet, and executive-level comfort.",
  "es": "Comodidad limpia, tranquila y de nivel ejecutivo.",
  "fr": "Un confort propre, calme et de niveau exécutif.",
  "ar": "راحة نظيفة وهادئة بمستوى تنفيذي.",
  "pt": "Conforto limpo, silencioso e de nível executivo.",
  "ur": "Clean, quiet, aur executive-level comfort.",
  "hi": "स्वच्छ, शांत और कार्यकारी स्तर का आराम।",
  "bn": "পরিষ্কার, শান্ত ও এক্সিকিউটিভ মানের আরাম।"
};
NOEL_I18N["class.hl1_title"] = {
  "en": "Professional chauffeurs", "es": "Chóferes profesionales", "fr": "Chauffeurs professionnels",
  "ar": "سائقون محترفون", "pt": "Motoristas profissionais",
  "ur": "Professional chauffeurs", "hi": "पेशेवर चालक", "bn": "পেশাদার চালক"
};
NOEL_I18N["class.hl1_text"] = {
  "en": "Polite, experienced chauffeurs who know the roads and respect your time.",
  "es": "Chóferes educados y experimentados que conocen las carreteras y respetan tu tiempo.",
  "fr": "Des chauffeurs polis et expérimentés qui connaissent les routes et respectent votre temps.",
  "ar": "سائقون مهذبون وذوو خبرة يعرفون الطرق ويحترمون وقتك.",
  "pt": "Motoristas educados e experientes que conhecem as estradas e respeitam seu tempo.",
  "ur": "Polite, experienced chauffeurs jo roads jaante hain aur aapke time ki izzat karte hain.",
  "hi": "विनम्र, अनुभवी चालक जो सड़कों को जानते हैं और आपके समय का सम्मान करते हैं।",
  "bn": "ভদ্র, অভিজ্ঞ চালক যারা রাস্তা জানেন এবং আপনার সময়কে সম্মান করেন।"
};
NOEL_I18N["class.hl2_title"] = {
  "en": "On-time pickups", "es": "Recogidas puntuales", "fr": "Prises en charge ponctuelles",
  "ar": "استلام في الوقت المحدد", "pt": "Coletas pontuais",
  "ur": "On-time pickups", "hi": "समय पर पिकअप", "bn": "সময়মতো পিকআপ"
};
NOEL_I18N["class.hl2_text"] = {
  "en": "Your chauffeur plans the route and arrives on time, every time.",
  "es": "Tu chófer planifica la ruta y llega a tiempo, siempre.",
  "fr": "Votre chauffeur planifie l'itinéraire et arrive à l'heure, à chaque fois.",
  "ar": "سائقك يخطط للطريق ويصل في الوقت المحدد، في كل مرة.",
  "pt": "Seu motorista planeja a rota e chega na hora, sempre.",
  "ur": "Aapka chauffeur route plan karta hai aur har baar time par pahunchta hai.",
  "hi": "आपका चालक मार्ग की योजना बनाता है और हर बार समय पर पहुँचता है।",
  "bn": "আপনার চালক রুট পরিকল্পনা করেন এবং প্রতিবার সময়মতো পৌঁছান।"
};
NOEL_I18N["class.hl3_title"] = {
  "en": "Recent high-end cars", "es": "Coches recientes de alta gama", "fr": "Voitures récentes haut de gamme",
  "ar": "سيارات حديثة فاخرة", "pt": "Carros recentes de alto padrão",
  "ur": "Recent high-end cars", "hi": "हाल की उच्च-स्तरीय कारें", "bn": "সাম্প্রতিক উচ্চমানের গাড়ি"
};
NOEL_I18N["class.hl3_text"] = {
  "en": "Clean, comfortable, recent cars, ready for every ride.",
  "es": "Coches limpios, cómodos y recientes, listos para cada viaje.",
  "fr": "Des voitures propres, confortables et récentes, prêtes pour chaque trajet.",
  "ar": "سيارات نظيفة ومريحة وحديثة، جاهزة لكل رحلة.",
  "pt": "Carros limpos, confortáveis e recentes, prontos para cada viagem.",
  "ur": "Clean, comfortable, recent cars, har ride ke liye ready.",
  "hi": "स्वच्छ, आरामदायक, हाल की कारें, हर सवारी के लिए तैयार।",
  "bn": "পরিষ্কার, আরামদায়ক, সাম্প্রতিক গাড়ি, প্রতিটি রাইডের জন্য প্রস্তুত।"
};
NOEL_I18N["class.hl4_title"] = {
  "en": "Arrive fully charged", "es": "Llega con la batería llena", "fr": "Arrivez avec le téléphone chargé",
  "ar": "صِل وهاتفك مشحون بالكامل", "pt": "Chegue com a bateria cheia",
  "ur": "Arrive fully charged", "hi": "पूरी तरह चार्ज होकर पहुँचें", "bn": "পুরো চার্জ নিয়ে পৌঁছান"
};
NOEL_I18N["class.hl4_text"] = {
  "en": "Phone chargers in every car, so your phone is full when you arrive.",
  "es": "Cargadores de teléfono en cada coche, para que tu teléfono esté lleno al llegar.",
  "fr": "Des chargeurs de téléphone dans chaque voiture, pour que votre téléphone soit chargé à l'arrivée.",
  "ar": "شواحن هواتف في كل سيارة، ليكون هاتفك مشحونًا بالكامل عند وصولك.",
  "pt": "Carregadores de telefone em cada carro, para que seu telefone esteja cheio ao chegar.",
  "ur": "Har gaari mein phone chargers, taaki aapke pahunchne par aapka phone full ho.",
  "hi": "हर कार में फ़ोन चार्जर, ताकि आपके पहुँचने पर आपका फ़ोन पूरा चार्ज हो।",
  "bn": "প্রতিটি গাড়িতে ফোন চার্জার, যাতে পৌঁছানোর সময় আপনার ফোন পুরো চার্জ থাকে।"
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
    { code: "bn", label: "Bengali", native: "বাংলা", dir: "ltr" }
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
    bn: ["জানুয়ারি", "ফেব্রুয়ারি", "মার্চ", "এপ্রিল", "মে", "জুন", "জুলাই", "আগস্ট", "সেপ্টেম্বর", "অক্টোবর", "নভেম্বর", "ডিসেম্বর"]
  },
  months_short: {
    en: ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"],
    es: ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sept", "oct", "nov", "dic"],
    fr: ["janv.", "févr.", "mars", "avr.", "mai", "juin", "juil.", "août", "sept.", "oct.", "nov.", "déc."],
    ar: ["يناير", "فبراير", "مارس", "أبريل", "مايو", "يونيو", "يوليو", "أغسطس", "سبتمبر", "أكتوبر", "نوفمبر", "ديسمبر"],
    pt: ["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"],
    ur: ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"],
    hi: ["जन", "फ़र", "मार्च", "अप्रैल", "मई", "जून", "जुला", "अग", "सितं", "अक्तू", "नवं", "दिसं"],
    bn: ["জানু", "ফেব্রু", "মার্চ", "এপ্রিল", "মে", "জুন", "জুলাই", "আগস্ট", "সেপ্টে", "অক্টো", "নভে", "ডিসে"]
  },
  days_short: {
    en: ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"],
    es: ["dom", "lun", "mar", "mié", "jue", "vie", "sáb"],
    fr: ["dim.", "lun.", "mar.", "mer.", "jeu.", "ven.", "sam."],
    ar: ["الأحد", "الاثنين", "الثلاثاء", "الأربعاء", "الخميس", "الجمعة", "السبت"],
    pt: ["dom", "seg", "ter", "qua", "qui", "sex", "sáb"],
    ur: ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"],
    hi: ["रवि", "सोम", "मंगल", "बुध", "गुरु", "शुक्र", "शनि"],
    bn: ["রবি", "সোম", "মঙ্গল", "বুধ", "বৃহস্পতি", "শুক্র", "শনি"]
  }
};
