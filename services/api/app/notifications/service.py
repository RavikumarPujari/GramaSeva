import uuid
from typing import Optional, List
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from app.models.issues import Notification

# Multilingual notification title & body templates
NOTIFICATION_TEMPLATES = {
    "SUBMISSION_RECEIVED": {
        "en": ("Complaint Submitted", "Your complaint #{ref} has been received and queued for Gram Panchayat review."),
        "kn": ("ದೂರು ಸಲ್ಲಿಸಲಾಗಿದೆ", "ನಿಮ್ಮ ದೂರು #{ref} ಸ್ವೀಕರಿಸಲ್ಪಟ್ಟಿದೆ ಮತ್ತು ಗ್ರಾಮ ಪಂಚಾಯತ್ ಪರಿಶೀಲನೆಗೆ ಸರದಿಯಲ್ಲಿದೆ."),
        "hi": ("शिकायत दर्ज की गई", "आपकी शिकायत #{ref} प्राप्त हो गई है और ग्राम पंचायत समीक्षा के लिए कतारबद्ध है।"),
    },
    "ISSUE_ASSIGNED": {
        "en": ("Team Assigned", "Issue #{ref} has been reviewed and assigned to the field department for repair."),
        "kn": ("ತಂಡ ನಿಯೋಜಿಸಲಾಗಿದೆ", "ಸಮಸ್ಯೆ #{ref} ಪರಿಶೀಲಿಸಲಾಗಿದೆ ಮತ್ತು ದುರಸ್ತಿಗಾಗಿ ಸಂಬಂಧಿತ ಇಲಾಖೆಗೆ ನಿಯೋಜಿಸಲಾಗಿದೆ."),
        "hi": ("टीम सौंपी गई", "शिकायत #{ref} की समीक्षा की गई है और मरम्मत के लिए संबंधित विभाग को सौंप दिया गया है।"),
    },
    "WORK_STARTED": {
        "en": ("Work In Progress", "Field team has commenced repair work on issue #{ref}."),
        "kn": ("ಕೆಲಸ ಪ್ರಗತಿಯಲ್ಲಿದೆ", "ಕ್ಷೇತ್ರ ಕಾರ್ಯಕರ್ತರು #{ref} ಸಮಸ್ಯೆಯ ದುರಸ್ತಿ ಕಾರ್ಯವನ್ನು ಪ್ರಾರಂಭಿಸಿದ್ದಾರೆ."),
        "hi": ("कार्य प्रगति पर है", "मैदानी टीम ने शिकायत #{ref} पर मरम्मत कार्य शुरू कर दिया है।"),
    },
    "REPAIR_REPORTED": {
        "en": ("Repair Completed (Awaiting Inspection)", "Field worker has submitted proof of repair for #{ref}. Pending independent verification."),
        "kn": ("ದುರಸ್ತಿ ವರದಿಯಾಗಿದೆ", "#{ref} ದುರಸ್ತಿ ಪುರಾವೆಯನ್ನು ಸಲ್ಲಿಸಲಾಗಿದೆ. ಸ್ವತಂತ್ರ ಪರಿಶೀಲನೆ ಬಾಕಿ ಇದೆ."),
        "hi": ("मरम्मत की सूचना दी गई", "#{ref} के लिए मरम्मत का प्रमाण प्रस्तुत किया गया है। स्वतंत्र सत्यापन लंबित है।"),
    },
    "RESOLUTION_APPROVED": {
        "en": ("Issue Resolved", "Repair for #{ref} was verified and approved by the supervisor. Please provide your feedback."),
        "kn": ("ಸಮಸ್ಯೆ ಪರಿಹರಿಸಲಾಗಿದೆ", "#{ref} ದುರಸ್ತಿಯನ್ನು ಮೇಲ್ವಿಚಾರಕರು ಪರಿಶೀಲಿಸಿ ಅನುಮೋದಿಸಿದ್ದಾರೆ. ದಯವಿಟ್ಟು ಪ್ರತಿಕ್ರಿಯೆ ನೀಡಿ."),
        "hi": ("समस्या का समाधान हुआ", "#{ref} की मरम्मत का पर्यवेक्षक द्वारा सत्यापन और अनुमोदन किया गया है। कृपया प्रतिक्रिया दें।"),
    },
    "ISSUE_REOPENED": {
        "en": ("Issue Reopened", "Complaint #{ref} was reopened following citizen dispute and queued for re-inspection."),
        "kn": ("ಸಮಸ್ಯೆ ಮರುತೆರೆಯಲಾಗಿದೆ", "ನಾಗರಿಕರ ಆಕ್ಷೇಪಣೆಯ ನಂತರ #{ref} ದೂರನ್ನು ಮರುಪರಿಶೀಲನೆಗಾಗಿ ಮರುತೆರೆಯಲಾಗಿದೆ."),
        "hi": ("शिकायत पुनः खोली गई", "नागरिक विवाद के बाद शिकायत #{ref} को फिर से जांच के लिए खोला गया है।"),
    },
    "SLA_OVERDUE": {
        "en": ("Operational Target Exceeded", "Issue #{ref} has exceeded its operational target SLA without resolution."),
        "kn": ("ಕಾರ್ಯಾಚರಣೆಯ ಗುರಿ ಮೀರಿದೆ", "ಸಮಸ್ಯೆ #{ref} ತನ್ನ ನಿಗದಿತ ಸಮಯದ ಮಿತಿಯನ್ನು ಮೀರಿದೆ."),
        "hi": ("परिचालन लक्ष्य समाप्त", "शिकायत #{ref} ने अपनी परिचालन लक्षित समय सीमा पार कर ली है।"),
    },
}

class NotificationService:
    @staticmethod
    def send_notification(
        db: Session,
        profile_id: str,
        event_type: str,
        reference_number: str,
        issue_id: Optional[str] = None,
        locale: str = "en",
        custom_title: Optional[str] = None,
        custom_message: Optional[str] = None,
        dedup_suffix: Optional[str] = None,
    ) -> Notification:
        """
        Creates an in-app notification with strict idempotency via dedup_key.
        If an event with this dedup_key was already created, the existing notification is returned.
        """
        norm_locale = locale if locale in ("en", "kn", "hi") else "en"
        dedup_key = f"{profile_id}:{event_type}:{issue_id or 'general'}:{dedup_suffix or 'default'}"

        # Check existing for idempotency
        existing = db.query(Notification).filter(Notification.dedup_key == dedup_key).first()
        if existing:
            return existing

        template = NOTIFICATION_TEMPLATES.get(event_type, {}).get(
            norm_locale,
            NOTIFICATION_TEMPLATES.get(event_type, {}).get("en", ("Notification", "Update on your issue"))
        )
        title = custom_title or template[0]
        message = custom_message or template[1].format(ref=reference_number)

        notif = Notification(
            id=str(uuid.uuid4()),
            profile_id=profile_id,
            issue_id=issue_id,
            event_type=event_type,
            title=title,
            message=message,
            locale=norm_locale,
            is_read=False,
            dedup_key=dedup_key,
        )
        db.add(notif)
        db.commit()
        db.refresh(notif)
        return notif

notification_service = NotificationService()
