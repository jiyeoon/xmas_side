from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.core.paginator import Paginator
from django.db.models import Q
import json

from .models import Post, PostImage, Comment
from members.models import Member


def board_list(request):
    """게시판 메인 페이지"""
    category = request.GET.get('category', 'all')
    view_type = request.GET.get('view', 'list')  # list or gallery
    search = request.GET.get('search', '')
    page = request.GET.get('page', 1)
    
    # 카테고리 필터링
    if category == 'all':
        posts = Post.objects.all()
    else:
        posts = Post.objects.filter(category=category)
    
    # 검색
    if search:
        posts = posts.filter(
            Q(title__icontains=search) | 
            Q(content__icontains=search) |
            Q(author_name__icontains=search)
        )
    
    # 페이지네이션
    paginator = Paginator(posts, 12)  # 12개씩
    page_obj = paginator.get_page(page)
    
    # 멤버 목록 (작성자 선택용)
    members = Member.objects.filter(status='active').order_by('name')
    
    context = {
        'posts': page_obj,
        'category': category,
        'view_type': view_type,
        'search': search,
        'members': members,
        'categories': Post.CATEGORY_CHOICES,
    }
    return render(request, 'board/board_list.html', context)


def post_detail(request, post_id):
    """게시글 상세"""
    post = get_object_or_404(Post, id=post_id)
    
    # 조회수 증가
    post.view_count += 1
    post.save(update_fields=['view_count'])
    
    # 이전/다음 글
    prev_post = Post.objects.filter(
        category=post.category, 
        created_at__lt=post.created_at
    ).first()
    next_post = Post.objects.filter(
        category=post.category, 
        created_at__gt=post.created_at
    ).order_by('created_at').first()
    
    context = {
        'post': post,
        'prev_post': prev_post,
        'next_post': next_post,
    }
    return render(request, 'board/post_detail.html', context)


def post_write(request, post_id=None):
    """글쓰기/수정 페이지"""
    category = request.GET.get('category', 'free')
    members = Member.objects.filter(status='active').order_by('name')
    
    post = None
    if post_id:
        post = get_object_or_404(Post, id=post_id)
        category = post.category
    
    context = {
        'category': category,
        'members': members,
        'post': post,  # 수정 모드일 때 기존 게시글 데이터
        'is_edit': post is not None,
    }
    return render(request, 'board/post_write.html', context)


@require_http_methods(["POST"])
def post_create(request):
    """게시글 작성 API"""
    try:
        title = request.POST.get('title', '').strip()
        content = request.POST.get('content', '').strip()
        category = request.POST.get('category', 'free')
        author_id = request.POST.get('author_id')
        author_name = request.POST.get('author_name', '').strip()
        password = request.POST.get('password', '').strip()
        is_pinned = request.POST.get('is_pinned') == 'true'
        
        if not title:
            return JsonResponse({'success': False, 'error': '제목을 입력해주세요.'})
        
        # 작성자 처리
        author = None
        if author_id:
            try:
                author = Member.objects.get(id=author_id)
                author_name = author.name
            except Member.DoesNotExist:
                pass
        
        if not author_name:
            author_name = '익명'
        
        # 게시글 생성
        post = Post.objects.create(
            title=title,
            content=content,
            category=category,
            author=author,
            author_name=author_name,
            password=password,
            is_pinned=is_pinned,
        )
        
        # 이미지 처리
        images = request.FILES.getlist('images')
        for i, image in enumerate(images):
            PostImage.objects.create(
                post=post,
                image=image,
                order=i
            )
        
        return JsonResponse({
            'success': True, 
            'post_id': post.id,
            'message': '게시글이 작성되었습니다.'
        })
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JsonResponse({'success': False, 'error': str(e)})


@require_http_methods(["POST"])
def post_update(request, post_id):
    """게시글 수정 API"""
    try:
        post = get_object_or_404(Post, id=post_id)
        
        # 비밀번호 확인
        password = request.POST.get('password', '').strip()
        if post.has_password() and not post.check_password(password):
            return JsonResponse({'success': False, 'error': '비밀번호가 일치하지 않습니다.', 'need_password': True})
        
        title = request.POST.get('title', '').strip()
        content = request.POST.get('content', '').strip()
        category = request.POST.get('category')
        is_pinned = request.POST.get('is_pinned') == 'true'
        
        if not title:
            return JsonResponse({'success': False, 'error': '제목을 입력해주세요.'})
        
        post.title = title
        post.content = content
        if category:
            post.category = category
        post.is_pinned = is_pinned
        post.save()
        
        # 새 이미지 추가
        images = request.FILES.getlist('images')
        max_order = post.images.count()
        for i, image in enumerate(images):
            PostImage.objects.create(
                post=post,
                image=image,
                order=max_order + i
            )
        
        # 삭제할 이미지 처리
        delete_image_ids = request.POST.get('delete_images', '')
        if delete_image_ids:
            ids = [int(id) for id in delete_image_ids.split(',') if id]
            PostImage.objects.filter(id__in=ids, post=post).delete()
        
        return JsonResponse({
            'success': True,
            'message': '게시글이 수정되었습니다.'
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@require_http_methods(["POST", "DELETE"])
def post_delete(request, post_id):
    """게시글 삭제 API"""
    try:
        post = get_object_or_404(Post, id=post_id)
        
        # 비밀번호 확인
        if request.content_type == 'application/json':
            data = json.loads(request.body)
            password = data.get('password', '')
        else:
            password = request.POST.get('password', '')
        
        if post.has_password() and not post.check_password(password):
            return JsonResponse({'success': False, 'error': '비밀번호가 일치하지 않습니다.', 'need_password': True})
        
        post.delete()
        return JsonResponse({
            'success': True,
            'message': '게시글이 삭제되었습니다.'
        })
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@require_http_methods(["POST"])
def check_password(request, post_id):
    """게시글 비밀번호 확인 API"""
    try:
        post = get_object_or_404(Post, id=post_id)
        data = json.loads(request.body)
        password = data.get('password', '')
        
        if not post.has_password():
            return JsonResponse({'success': True, 'has_password': False})
        
        if post.check_password(password):
            return JsonResponse({'success': True, 'has_password': True})
        else:
            return JsonResponse({'success': False, 'error': '비밀번호가 일치하지 않습니다.'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@require_http_methods(["POST"])
def comment_create(request, post_id):
    """댓글 작성 API"""
    try:
        post = get_object_or_404(Post, id=post_id)
        data = json.loads(request.body)
        
        content = data.get('content', '').strip()
        author_id = data.get('author_id')
        author_name = data.get('author_name', '').strip()
        
        if not content:
            return JsonResponse({'success': False, 'error': '내용을 입력해주세요.'})
        
        # 작성자 처리
        author = None
        if author_id:
            try:
                author = Member.objects.get(id=author_id)
                author_name = author.name
            except Member.DoesNotExist:
                pass
        
        if not author_name:
            author_name = '익명'
        
        comment = Comment.objects.create(
            post=post,
            author=author,
            author_name=author_name,
            content=content,
        )
        
        return JsonResponse({
            'success': True,
            'comment': {
                'id': comment.id,
                'author_name': comment.author_name,
                'content': comment.content,
                'created_at': comment.created_at.strftime('%Y-%m-%d %H:%M'),
            }
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@require_http_methods(["POST", "DELETE"])
def comment_delete(request, comment_id):
    """댓글 삭제 API"""
    try:
        comment = get_object_or_404(Comment, id=comment_id)
        comment.delete()
        return JsonResponse({
            'success': True,
            'message': '댓글이 삭제되었습니다.'
        })
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


def api_posts(request):
    """게시글 목록 API (AJAX용)"""
    category = request.GET.get('category', 'all')
    page = request.GET.get('page', 1)
    search = request.GET.get('search', '')
    
    if category == 'all':
        posts = Post.objects.all()
    else:
        posts = Post.objects.filter(category=category)
    
    if search:
        posts = posts.filter(
            Q(title__icontains=search) | 
            Q(content__icontains=search)
        )
    
    paginator = Paginator(posts, 12)
    page_obj = paginator.get_page(page)
    
    posts_data = []
    for post in page_obj:
        first_image = post.images.first()
        posts_data.append({
            'id': post.id,
            'title': post.title,
            'content': post.content[:100] + '...' if len(post.content) > 100 else post.content,
            'category': post.category,
            'category_display': post.get_category_display(),
            'author_name': post.author_name,
            'view_count': post.view_count,
            'comment_count': post.comments.count(),
            'image_count': post.images.count(),
            'first_image': first_image.image.url if first_image else None,
            'is_pinned': post.is_pinned,
            'created_at': post.created_at.strftime('%Y-%m-%d %H:%M'),
        })
    
    return JsonResponse({
        'posts': posts_data,
        'has_next': page_obj.has_next(),
        'has_previous': page_obj.has_previous(),
        'total_pages': paginator.num_pages,
        'current_page': page_obj.number,
    })
