# rest_framework에서 serializers 모듈을 가져옵니다.
# serializers는 Django 모델 인스턴스나 쿼리셋을 JSON 같은 형태로 변환해주는 역할을 합니다.
from rest_framework import serializers
# reviews 앱의 models.py에서 Review와 Comment 모델을 가져옵니다.
from reviews.models import Review, Comment
from django.contrib.auth import get_user_model

# 사용자 정보를 위한 간단한 Serializer입니다.
# 다른 Serializer에서 이 Serializer를 중첩하여 사용하여 코드 중복을 줄입니다.
class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = get_user_model()
        fields = ['id', 'username']

# 댓글 상세 정보를 보여줄 때 사용하는 Serializer입니다.
class CommentDetailSerializer(serializers.ModelSerializer):
    # 중첩된 Serializer를 사용하여 댓글 작성자의 정보를 포함시킵니다.
    # read_only=True로 설정하여, 댓글 조회 시에만 사용자 정보가 보이고,
    # 댓글 생성/수정 시에는 이 필드를 통해 사용자 정보를 변경할 수 없도록 합니다.
    user = UserSerializer(read_only=True)

    class Meta:
        # 이 Serializer가 Comment 모델을 기반으로 동작함을 명시합니다.
        model = Comment
        # API를 통해 보여줄 필드들을 나열합니다.
        fields = ['id', 'user', 'content', 'created_at', 'updated_at']
        # content를 제외한 모든 필드는 읽기 전용입니다.
        read_only_fields = ['id', 'user', 'created_at', 'updated_at']


# 새로운 댓글을 생성하거나 기존 댓글을 수정할 때 사용하는 Serializer입니다.
class CommentWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Comment
        # 클라이언트가 직접 작성/수정할 수 있는 'content' 필드만 포함합니다.
        # 'user'와 'review' 필드는 ViewSet에서 자동으로 채워줍니다.
        fields = ['content']


# 여러 개의 Review 객체를 목록 형태로 보여줄 때 사용하는 Serializer입니다.
class ReviewListSerializer(serializers.ModelSerializer):
    # 리뷰 작성자 정보를 중첩된 형태로 보여줍니다.
    user = UserSerializer(read_only=True)

    class Meta:
        # 이 Serializer가 Review 모델을 기반으로 동작함을 명시합니다.
        model = Review
        # 리뷰 목록에서 보여줄 필드들을 지정합니다.
        # 기존의 HyperlinkedRelatedField 대신 pk 필드를 직접 노출하는 것이
        # SPA(Single Page Application) 프론트엔드와 연동하기 더 수월한 경우가 많습니다.
        fields = ['id', 'title', 'content', 'user', 'video_id']


# 단일 Review 객체의 상세 정보를 보여줄 때 사용하는 Serializer입니다.
class ReviewDetailSerializer(serializers.ModelSerializer):
    # 리뷰 작성자 정보를 중첩된 형태로 보여줍니다.
    user = UserSerializer(read_only=True)
    # 이 리뷰에 달린 모든 댓글들을 포함시킵니다.
    # CommentDetailSerializer를 사용하여 각 댓글을 직렬화합니다.
    comments = CommentDetailSerializer(many=True, read_only=True)

    class Meta:
        # 이 Serializer가 Review 모델을 기반으로 동작함을 명시합니다.
        model = Review
        # 리뷰 상세 정보에서 보여줄 모든 필드들을 나열합니다.
        fields = [
            'id', 'user', 'title', 'content', 'video_id', 'lang_code',
            'comments', 'created_at', 'updated_at'
        ]


# 새로운 Review를 생성하거나 기존 Review를 수정할 때 사용하는 Serializer입니다.
class ReviewCreateUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        # 이 Serializer가 Review 모델을 기반으로 동작함을 명시합니다.
        model = Review
        # 클라이언트가 직접 생성하거나 수정할 수 있는 필드들만 지정합니다.
        fields = ['video_id', 'lang_code', 'title', 'content']