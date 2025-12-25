from rest_framework import permissions

class IsOwnerOrReadOnly(permissions.BasePermission):
    """
    객체의 소유자에게만 쓰기 권한을 부여하는 커스텀 권한입니다.
    읽기 권한은 모든 사용자에게 허용됩니다.
    """

    def has_object_permission(self, request, view, obj):
        # GET, HEAD, OPTIONS 요청과 같은 안전한 메서드는 항상 허용합니다.
        # 즉, 모든 사용자가 댓글 목록과 상세 정보를 볼 수 있습니다.
        if request.method in permissions.SAFE_METHODS:
            return True

        # 쓰기 권한(수정, 삭제 등)은 객체(obj)의 소유자(user)와
        # 현재 요청을 보낸 사용자(request.user)가 동일한 경우에만 부여합니다.
        return obj.user == request.user
