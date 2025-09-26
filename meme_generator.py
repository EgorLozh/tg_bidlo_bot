import asyncio
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont
import aiohttp
import logging

class MemeGenerator:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.default_font_path = "meme/a_FuturicaBlack.ttf"
        
        # Доступные шаблоны мемов (URL или локальные пути)
        self.templates = {
            "default": "meme/photo_2025-05-27_19-06-15.jpg",
        }
    
    async def get_available_templates(self) -> list:
        """Получить список доступных шаблонов"""
        return list(self.templates.keys())
    
    async def create_meme_from_template(self, template_name: str, text: str) -> bytes:
        """Создать мем на основе шаблона"""
        try:
            # Загрузка шаблона
            if template_name not in self.templates:
                template_name = "default"
            
            # Создание мема
            image = Image.open(self.templates[template_name])
            meme_image = await self._add_text_to_image(image, text)
            
            # Конвертация в bytes
            output = BytesIO()
            meme_image.save(output, format='JPEG', quality=85)
            return output.getvalue()
            
        except Exception as e:
            self.logger.error(f"Error creating meme from template: {e}")
            # Fallback - создаем простой мем с цветным фоном
            return await self._create_fallback_meme(text)
    
    async def create_meme_from_image(self, image_data: bytes, text: str) -> bytes:
        """Создать мем на основе пользовательского изображения"""
        try:
            image = Image.open(BytesIO(image_data))
            meme_image = await self._add_text_to_image(image, text)
            
            output = BytesIO()
            meme_image.save(output, format='JPEG', quality=85)
            return output.getvalue()
            
        except Exception as e:
            self.logger.error(f"Error creating meme from image: {e}")
            return await self._create_fallback_meme(text)
    
    async def _add_text_to_image(self, image: Image.Image, text: str) -> Image.Image:
        """Добавить текст к изображению"""
        draw = ImageDraw.Draw(image)
        
        # Настройки шрифта
        try:
            font_size = max(20, min(image.width // 15, 60))
            font = ImageFont.truetype(self.default_font_path, font_size)
        except:
            font = ImageFont.load_default()
        
        # Разбиваем текст на строки
        max_chars_per_line = image.width // (font_size // 2)
        words = text.split()
        lines = []
        current_line = []
        
        for word in words:
            if len(' '.join(current_line + [word])) <= max_chars_per_line:
                current_line.append(word)
            else:
                lines.append(' '.join(current_line))
                current_line = [word]
        if current_line:
            lines.append(' '.join(current_line))
        
        # Рисуем текст на изображении
        text_color = (255, 255, 255)     # белый 
        stroke_color = (0, 0, 0)  # черный
        stroke_width = 2
        
        y_position = 10
        for line in lines:
            # Вычисляем позицию текста
            bbox = draw.textbbox((0, 0), line, font=font)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]
            x_position = (image.width - text_width) // 2
            
            # Рисуем обводку и текст
            draw.text((x_position, y_position), line, font=font, 
                     fill=text_color, stroke_fill=stroke_color, stroke_width=stroke_width)
            y_position += text_height + 5
        
        return image
    
    async def _create_fallback_meme(self, text: str) -> bytes:
        """Создать простой мем с цветным фоном (fallback)"""
        image = Image.new('RGB', (800, 600), color=(73, 109, 137))
        draw = ImageDraw.Draw(image)
        
        try:
            font = ImageFont.truetype(self.default_font_path, 40)
        except:
            font = ImageFont.load_default()
        
        draw.text((400, 300), text, font=font, fill=(255, 255, 255), anchor="mm")
        
        output = BytesIO()
        image.save(output, format='JPEG', quality=85)
        return output.getvalue()