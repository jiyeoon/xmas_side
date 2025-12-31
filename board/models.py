from django.db import models
from members.models import Member
import re


class Post(models.Model):
    """게시글 모델"""
    
    CATEGORY_CHOICES = [
        ('notice', '공지사항'),
        ('free', '자유게시판'),
        ('gallery', '사진갤러리'),
    ]
    
    title = models.CharField(max_length=200, verbose_name='제목')
    content = models.TextField(verbose_name='내용', blank=True)
    category = models.CharField(
        max_length=20, 
        choices=CATEGORY_CHOICES, 
        default='free',
        verbose_name='카테고리'
    )
    author = models.ForeignKey(
        Member, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='posts',
        verbose_name='작성자'
    )
    author_name = models.CharField(max_length=50, blank=True, verbose_name='작성자명')
    password = models.CharField(max_length=100, blank=True, verbose_name='비밀번호')
    is_pinned = models.BooleanField(default=False, verbose_name='상단 고정')
    view_count = models.PositiveIntegerField(default=0, verbose_name='조회수')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='작성일')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='수정일')
    
    class Meta:
        ordering = ['-is_pinned', '-created_at']
        verbose_name = '게시글'
        verbose_name_plural = '게시글'
    
    def __str__(self):
        return self.title
    
    def save(self, *args, **kwargs):
        # author가 있으면 author_name 자동 설정
        if self.author and not self.author_name:
            self.author_name = self.author.name
        super().save(*args, **kwargs)
    
    def has_password(self):
        """비밀번호가 설정되어 있는지 확인"""
        return bool(self.password)
    
    def check_password(self, password):
        """비밀번호 확인"""
        if not self.password:
            return True  # 비밀번호가 없으면 항상 통과
        # 타입 변환하여 비교 (숫자로 입력해도 문자열로 비교)
        return str(self.password) == str(password)
    
    def get_thumbnail_url(self):
        """본문에서 첫 번째 이미지 URL 추출"""
        # 1. PostImage에서 먼저 찾기
        first_image = self.images.first()
        if first_image:
            return first_image.image.url
        
        # 2. 본문 content에서 <img> 태그의 src 추출
        if self.content:
            # <img src="..."> 패턴 찾기
            img_pattern = r'<img[^>]+src=["\']([^"\']+)["\']'
            match = re.search(img_pattern, self.content)
            if match:
                return match.group(1)
        
        return None
    
    def get_image_count(self):
        """본문의 이미지 개수 반환"""
        count = self.images.count()
        if self.content:
            # 본문의 <img> 태그 개수
            count += len(re.findall(r'<img[^>]+>', self.content))
        return count


class PostImage(models.Model):
    """게시글 이미지"""
    
    post = models.ForeignKey(
        Post, 
        on_delete=models.CASCADE, 
        related_name='images',
        verbose_name='게시글'
    )
    image = models.ImageField(upload_to='board/%Y/%m/', verbose_name='이미지')
    order = models.PositiveIntegerField(default=0, verbose_name='순서')
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['order', 'created_at']
        verbose_name = '게시글 이미지'
        verbose_name_plural = '게시글 이미지'
    
    def __str__(self):
        return f"{self.post.title} - 이미지 {self.order}"


class Comment(models.Model):
    """댓글 모델"""
    
    post = models.ForeignKey(
        Post, 
        on_delete=models.CASCADE, 
        related_name='comments',
        verbose_name='게시글'
    )
    author = models.ForeignKey(
        Member, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='comments',
        verbose_name='작성자'
    )
    author_name = models.CharField(max_length=50, blank=True, verbose_name='작성자명')
    content = models.TextField(verbose_name='내용')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='작성일')
    
    class Meta:
        ordering = ['created_at']
        verbose_name = '댓글'
        verbose_name_plural = '댓글'
    
    def __str__(self):
        return f"{self.post.title} - {self.author_name}"
    
    def save(self, *args, **kwargs):
        if self.author and not self.author_name:
            self.author_name = self.author.name
        super().save(*args, **kwargs)
