def format_medcard_for_chat(medcard_data: dict) -> str:
    """Форматирует медкарту в красивое сообщение для чата"""
    
    lines = ["📋 МЕДИЦИНСКАЯ КАРТА", ""]
    
    # 1. Базовая информация
    if medcard_data.get('full_name'):
        lines.append(f"👤 ФИО: {medcard_data['full_name']}")
    if medcard_data.get('age'):
        lines.append(f"🎂 Возраст: {medcard_data['age']} лет")
    if medcard_data.get('home_address'):
        lines.append(f"🏠 Адрес: {medcard_data['home_address']}")
    
    lines.append("")
    
    # 2. Группа крови
    if medcard_data.get('blood_type') or medcard_data.get('rhesus_factor'):
        blood = medcard_data.get('blood_type', '?')
        rhesus = medcard_data.get('rhesus_factor', '?')
        lines.append(f"🩸 Группа крови: {blood} ({rhesus})")
        lines.append("")
    
    # 3. Экстренные контакты
    contacts = medcard_data.get('emergency_contacts', [])
    if contacts:
        lines.append("🚨 ЭКСТРЕННЫЕ КОНТАКТЫ:")
        for contact in contacts:
            priority_emoji = ["🔴", "🟠", "🔵"][contact.get('priority', 1) - 1]
            name = contact.get('name', 'Не указано')
            phone = contact.get('phone', 'Не указан')
            relation = contact.get('relation', '')
            
            if relation:
                lines.append(f"{priority_emoji} {name} ({relation}): {phone}")
            else:
                lines.append(f"{priority_emoji} {name}: {phone}")
        lines.append("")
    
    # 4. Диагноз
    if medcard_data.get('current_diagnosis'):
        lines.append(f"🏥 Диагноз: {medcard_data['current_diagnosis']}")
        lines.append("")
    
    # 5. Хронические заболевания
    chronic = medcard_data.get('chronic_diseases', [])
    if chronic:
        lines.append("⚠️ Хронические заболевания:")
        for disease in chronic:
            lines.append(f"  • {disease}")
        lines.append("")
    
    # 6. Аллергии
    allergies = medcard_data.get('allergies', [])
    if allergies:
        lines.append("🚫 АЛЛЕРГИИ:")
        for allergy in allergies:
            lines.append(f"  • {allergy}")
        lines.append("")
    
    # 7. Индивидуальные особенности
    if medcard_data.get('special_features'):
        lines.append(f"ℹ️ Особенности: {medcard_data['special_features']}")
        lines.append("")
    
    # 8. Лекарства
    medications = medcard_data.get('medications', [])
    if medications:
        lines.append("💊 ПРИНИМАЕМЫЕ ЛЕКАРСТВА:")
        for med in medications:
            name = med.get('name', 'Не указано')
            dosage = med.get('dosage', '')
            frequency = med.get('frequency', '')
            notes = med.get('notes', '')
            
            lines.append(f"  • {name}")
            if dosage:
                lines.append(f"    Доза: {dosage}")
            if frequency:
                lines.append(f"    Частота: {frequency}")
            if notes:
                lines.append(f"    Примечание: {notes}")
        lines.append("")
    
    lines.append("─────────────────────")
    lines.append("⚕️ При необходимости свяжитесь с экстренными контактами")
    
    return "\n".join(lines)