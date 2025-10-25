"""
Certificate generation service
Generates personalized certificates for course completion
"""
import logging
from pathlib import Path
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont
from typing import Optional

from bot.config import CERTIFICATES_PATH, LIBERATION_CODE

logger = logging.getLogger(__name__)


class CertificateService:
    """Service for generating certificates"""

    def __init__(self, template_path: str = None):
        """
        Initialize certificate service

        Args:
            template_path: Path to certificate template image
        """
        if template_path:
            self.template_path = Path(template_path)
        else:
            # Default template path - Purple and Blue Technology Certificate
            self.template_path = Path(__file__).parent.parent.parent / "docs" / "certificate_template.png"

        if not self.template_path.exists():
            logger.error(f"Certificate template not found: {self.template_path}")

        # Ensure certificates directory exists
        Path(CERTIFICATES_PATH).mkdir(parents=True, exist_ok=True)

    def generate_certificate(
        self,
        user_name: str,
        telegram_id: int,
        completion_date: datetime = None,
        total_days: int = 10,
        accuracy: float = 0.0,
        liberation_code: str = LIBERATION_CODE
    ) -> Optional[Path]:
        """
        Generate personalized certificate

        Args:
            user_name: User's name
            telegram_id: User's Telegram ID
            completion_date: Course completion date
            total_days: Total days completed
            accuracy: Task accuracy percentage
            liberation_code: Collected liberation code

        Returns:
            Path to generated certificate or None if failed
        """
        try:
            # Load template
            if not self.template_path.exists():
                logger.error(f"Template not found: {self.template_path}")
                return None

            img = Image.open(self.template_path)
            draw = ImageDraw.Draw(img)

            # Try to load fonts (fallback to default if not found)
            try:
                # For user name - large, bold
                font_name_large = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 60)
                font_name_medium = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 48)
                font_name_small = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 36)

                # For other text
                font_text = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 24)
                font_small = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 18)
            except Exception as e:
                logger.warning(f"Could not load custom fonts: {e}. Using default.")
                font_name_large = ImageFont.load_default()
                font_name_medium = ImageFont.load_default()
                font_name_small = ImageFont.load_default()
                font_text = ImageFont.load_default()
                font_small = ImageFont.load_default()

            # Get image dimensions
            width, height = img.size

            # Colors for new Purple and Blue template
            color_white = "#FFFFFF"      # White for name
            color_cyan = "#00D9FF"       # Cyan for additional info
            color_light_blue = "#7FB5FF" # Light blue for date

            # User name (not uppercase for this template)
            user_display_name = user_name

            # Try fonts from largest to smallest to fit the name
            name_font = font_name_medium  # Start with medium for elegance
            bbox = draw.textbbox((0, 0), user_display_name, font=name_font)
            text_width = bbox[2] - bbox[0]

            # If too wide, use smaller font
            if text_width > width * 0.7:
                name_font = font_name_small
                bbox = draw.textbbox((0, 0), user_display_name, font=name_font)
                text_width = bbox[2] - bbox[0]

            # Position for user name
            # Based on Purple and Blue template, name goes after "Dear" text
            # "Dear" is at approximately y=139 (20% from top)
            name_x = width // 2
            name_y = int(height * 0.38) + 100  # Adjusted 100px lower as requested

            # Draw user name (centered, white color)
            draw.text(
                (name_x, name_y),
                user_display_name,
                font=name_font,
                fill=color_white,
                anchor="mm"  # middle-middle (centered)
            )

            # Add completion info at the bottom
            if completion_date:
                date_text = f"{completion_date.strftime('%d.%m.%Y')}"
            else:
                date_text = f"{datetime.now().strftime('%d.%m.%Y')}"

            # Additional info positioned at the bottom
            # Bottom section starts around 85% of height
            bottom_start = int(height * 0.85)

            # Liberation code (centered, cyan, slightly above bottom)
            code_text = f"CODE: {liberation_code}"
            draw.text(
                (width // 2, bottom_start),
                code_text,
                font=font_text,
                fill=color_cyan,
                anchor="mm"
            )

            # Completion date (centered, light blue)
            draw.text(
                (width // 2, bottom_start + 35),
                date_text,
                font=font_small,
                fill=color_light_blue,
                anchor="mm"
            )

            # Generate unique filename
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"certificate_{telegram_id}_{timestamp}.png"
            output_path = Path(CERTIFICATES_PATH) / filename

            # Save certificate
            img.save(output_path, 'PNG')

            logger.info(f"✅ Certificate generated: {output_path}")
            return output_path

        except Exception as e:
            logger.error(f"Error generating certificate: {e}")
            return None

    def generate_certificate_simple(
        self,
        user_name: str,
        telegram_id: int
    ) -> Optional[Path]:
        """
        Generate simple certificate with minimal info

        Args:
            user_name: User's name
            telegram_id: User's Telegram ID

        Returns:
            Path to generated certificate
        """
        return self.generate_certificate(
            user_name=user_name,
            telegram_id=telegram_id,
            completion_date=datetime.now(),
            total_days=10,
            accuracy=100.0,
            liberation_code=LIBERATION_CODE
        )


# Global certificate service instance
certificate_service = CertificateService()


async def generate_user_certificate(
    user_name: str,
    telegram_id: int,
    completion_date: datetime = None,
    total_days: int = 10,
    accuracy: float = 100.0,
    liberation_code: str = LIBERATION_CODE
) -> Optional[Path]:
    """
    Async wrapper for certificate generation

    Args:
        user_name: User's name
        telegram_id: User's Telegram ID
        completion_date: Completion date
        total_days: Days completed
        accuracy: Task accuracy
        liberation_code: Liberation code

    Returns:
        Path to certificate or None
    """
    return certificate_service.generate_certificate(
        user_name=user_name,
        telegram_id=telegram_id,
        completion_date=completion_date,
        total_days=total_days,
        accuracy=accuracy,
        liberation_code=liberation_code
    )
