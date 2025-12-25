from django.shortcuts import (
    render,
    redirect,
    get_object_or_404,
)  # get_object_or_404 임포트
from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse
from django.views.decorators.cache import never_cache
from django.contrib import messages  # messages 임포트
from .models import Review, Comment
from .forms import ReviewForm, CommentForm


# Create your views here.
def index(req: HttpRequest) -> HttpResponse:
    """게시글 전체를 조회하는 함수"""
    reviews = Review.objects.all().order_by("created_at").reverse()

    context = {
        "reviews": reviews,
    }
    return render(req, "reviews/index.html", context)


def detail(req: HttpRequest, review_pk: int) -> HttpResponse:

    review: Review = get_object_or_404(Review, pk=review_pk)
    comments = review.comments.all()  # 해당 리뷰의 모든 댓글 가져오기
    comment_form = CommentForm()

    context = {
        "review": review,
        "comments": comments,  # 댓글 목록을 컨텍스트에 추가
        "comment_form": comment_form,
    }

    return render(req, "reviews/detail.html", context)


@login_required
@never_cache  # 뒤로가기 시 캐시된 폼 데이터가 나타나는 것을 방지
def create(req: HttpRequest) -> HttpResponse:

    if req.method == "POST":
        form = ReviewForm(req.POST)
        if form.is_valid():
            review: Review = form.save(commit=False)
            review.user = req.user
            review.save()
            messages.success(req, "리뷰가 성공적으로 작성되었습니다.")  # 성공 메시지 추가
            req.session["review_created_just_now"] = True  # 세션 플래그 설정
            return redirect("reviews:detail", review.pk)  # PRG redirect
    else:
        # GET 요청 (뒤로가기 포함)
        if req.session.pop("review_created_just_now", False):
            # 방금 리뷰를 작성하고 뒤로가기 한 경우
            messages.info(
                req,
                "리뷰 작성을 완료했습니다. 새로운 리뷰를 작성하시려면 다시 시도해주세요.",
            )
            return redirect("reviews:index")  # 리뷰 목록 페이지로 리다이렉트
        review_form = ReviewForm()

    context = {
        "review_form": review_form,
    }

    return render(req, "reviews/create.html", context)


@login_required
def update(req: HttpRequest, review_pk: int) -> HttpResponse:  
    review = get_object_or_404(Review, pk=review_pk)
    if req.user != review.user:
        # 권한이 없는 경우 처리 (예: 403 Forbidden 응답)
        # from django.http import HttpResponseForbidden
        # return HttpResponseForbidden()
        return redirect("reviews:detail", review_pk)

    if req.method == "POST":
        # POST 요청: 폼을 제출하여 리뷰를 수정
        form = ReviewForm(req.POST, instance=review)
        if form.is_valid():
            form.save()
            return redirect("reviews:detail", review_pk)
    else:
        # GET 요청: 기존 리뷰 내용으로 채워진 폼을 표시
        form = ReviewForm(instance=review)

    context = {
        "review": review,
        "review_form": form,
    }
    return render(req, "reviews/update.html", context)


@login_required
def delete(req: HttpRequest, review_pk: int) -> HttpResponse:
    review = get_object_or_404(Review, pk=review_pk)

    if review.user == req.user:
        review.delete()

    return redirect("reviews:index")


def create_comment(req: HttpRequest, review_pk: int) -> HttpResponse:
    review: Review = get_object_or_404(Review, pk=review_pk)
    comment_form = CommentForm(req.POST)

    if comment_form.is_valid():

        comment: Comment = comment_form.save(commit=False)
        comment.review = review
        comment.user = req.user
        comment.save()
        return redirect("reviews:detail", review.pk)
    context = {
        "review": review,
        "comment_form": comment_form,
    }

    return render(req, "reviews/detail.html", context)


@login_required
def delete_comment(req: HttpRequest, review_pk: int, comment_pk: int) -> HttpResponse:
    # 1. 삭제는 POST 요청으로만 허용
    if req.method != "POST":
        messages.error(req, "잘못된 접근입니다. 댓글 삭제는 POST 요청으로만 가능합니다.")
        return redirect("reviews:detail", review_pk)

    # 2. 리뷰 객체 조회 (존재하지 않으면 404 에러)
    review = get_object_or_404(Review, pk=review_pk)

    # 3. 댓글 객체 조회 (comment_pk와 review 객체를 모두 사용하여 보안 강화)
    #    댓글이 존재하지 않거나 해당 리뷰에 속하지 않으면 404 에러
    comment = get_object_or_404(Comment, pk=comment_pk, review=review)

    # 4. 권한 확인: 댓글 작성자만 삭제 가능
    if comment.user != req.user:
        messages.error(req, "댓글을 삭제할 권한이 없습니다.")
        # return HttpResponseForbidden("댓글을 삭제할 권한이 없습니다.") # 403 에러를 원한다면 사용
        return redirect(
            "reviews:detail", review_pk
        )  # 권한 없으면 상세 페이지로 리다이렉트

    # 5. 댓글 삭제
    comment.delete()
    messages.success(req, "댓글이 성공적으로 삭제되었습니다.")
    return redirect(
        "reviews:detail", review_pk
    )  # 삭제 후 리뷰 상세 페이지로 리다이렉트





##########################################
# 이 부분 이하는 Rest Framework를 위한 부분입니다#
##########################################


from rest_framework.views import APIView
from rest_framework.response import Response
# generics와 IsAuthenticated를 import합니다.
from rest_framework import status, viewsets
from rest_framework.permissions import IsAuthenticatedOrReadOnly
# TokenAuthentication을 import합니다.
from rest_framework.authentication import TokenAuthentication
# 필요한 Serializer들을 모두 import합니다.
from .serializers import (
    ReviewListSerializer,
    ReviewDetailSerializer,
    ReviewCreateUpdateSerializer,
    CommentDetailSerializer,
    CommentWriteSerializer,
)
from .permissions import IsOwnerOrReadOnly  # IsOwnerOrReadOnly 권한을 import합니다.

class ReviewViewSet(viewsets.ModelViewSet):
    """
    Review 모델에 대한 CRUD API를 제공하는 ViewSet입니다.
    """
    queryset = Review.objects.all().order_by("-created_at")
    # 인증 설정: 토큰 인증을 사용하도록 명시합니다.
    # 클라이언트는 헤더에 'Authorization: Token <토큰값>' 형태로 요청을 보내야 합니다.
    authentication_classes = [TokenAuthentication]
    # 권한 설정: 읽기는 누구나, 생성/수정/삭제는 인증된 사용자 + 본인만 가능
    permission_classes = [IsAuthenticatedOrReadOnly, IsOwnerOrReadOnly]

    def get_serializer_class(self):
        # 'list' (목록 조회) 액션일 때는 ReviewListSerializer를 사용합니다.
        if self.action == "list":
            return ReviewListSerializer
        # 'retrieve' (상세 조회) 액션일 때는 ReviewDetailSerializer를 사용합니다.
        elif self.action == "retrieve":
            return ReviewDetailSerializer
        # 'create', 'update', 'partial_update' (생성, 수정) 액션일 때는
        # ReviewCreateUpdateSerializer를 사용합니다.
        return ReviewCreateUpdateSerializer

    # Review 생성 시 현재 로그인된 사용자를 작성자로 자동 할당합니다.
    # 토큰 인증이 성공하면 request.user에 해당 토큰의 주인(User)이 자동으로 할당됩니다.
    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class CommentViewSet(viewsets.ModelViewSet):
    """
    특정 Review에 대한 Comment의 목록 조회, 생성, 수정, 삭제 API를 제공하는 ViewSet입니다.
    """
    # 인증 설정: 토큰 인증을 사용하도록 명시합니다.
    authentication_classes = [TokenAuthentication]
    # 권한 설정: 읽기는 누구나, 생성/수정/삭제는 인증된 사용자 + 본인만 가능
    permission_classes = [IsAuthenticatedOrReadOnly, IsOwnerOrReadOnly]

    def get_serializer_class(self):
        # 쓰기 작업(create, update, partial_update)에는 CommentWriteSerializer를 사용합니다.
        if self.action in ['create', 'update', 'partial_update']:
            return CommentWriteSerializer
        # 그 외 읽기 작업(list, retrieve)에는 CommentDetailSerializer를 사용합니다.
        return CommentDetailSerializer

    def get_queryset(self):
        """
        이 ViewSet에서 반환할 객체 목록을 결정합니다.
        URL에 포함된 review_pk를 사용하여 해당 리뷰에 달린 댓글만 필터링합니다.
        """
        # URL 경로에서 'review_pk' 값을 가져옵니다.
        review_pk = self.kwargs.get("review_pk")
        # 해당 review_pk를 가진 리뷰를 찾습니다. 없으면 404 에러를 발생시킵니다.
        review = get_object_or_404(Review, pk=review_pk)
        # 해당 리뷰에 속한 댓글들만 최신순으로 정렬하여 반환합니다.
        return review.comments.all().order_by('-created_at')

    def perform_create(self, serializer):
        """
        새로운 댓글 객체가 저장될 때 호출됩니다.
        댓글에 리뷰와 작성자 정보를 자동으로 할당합니다.
        """
        # URL 경로에서 'review_pk' 값을 가져와 해당 Review 객체를 찾습니다.
        review = get_object_or_404(Review, pk=self.kwargs.get("review_pk"))
        # serializer.save()가 호출될 때, user와 review 필드를 자동으로 채워줍니다.
        serializer.save(user=self.request.user, review=review)

