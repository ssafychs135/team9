from django import forms
from .models import Review, Comment


class ReviewForm(forms.ModelForm):
    class Meta:
        model = Review
        # fields = '__all__' 과 유사하게 동작하지만, 명시된 필드만 제외합니다.
        exclude = ('user',)
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '리뷰 제목을 입력하세요.'}),
            'content': forms.Textarea(attrs={'class': 'form-control', 'placeholder': '리뷰 내용을 입력하세요.'}),
            'video_id': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'YouTube 영상 ID를 입력하세요.'}),
            'lang_code': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '언어 코드를 입력하세요 (예: en, ko).'}),
        }


class CommentForm(forms.ModelForm):
    class Meta:
        model = Comment
        # fields = '__all__' 과 유사하게 동작하지만, 명시된 필드만 제외합니다.
        exclude = ('user','review')
        widgets = {
            'content': forms.Textarea(attrs={'class': 'form-control', 'placeholder': '댓글을 입력하세요.'}),
        }
