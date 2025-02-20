document.addEventListener('DOMContentLoaded', function () {
    const searchInput = document.getElementById('searchInput');
    const generateBtn = document.getElementById('generateBtn');

    async function generateImage() {
        const prompt = searchInput.value.trim();

        if (!prompt) {
            alert('프롬프트를 입력해주세요.');
            return;
        }

        generateBtn.disabled = true;
        const originalText = generateBtn.innerHTML;
        generateBtn.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> 생성중...';

        try {
            const csrfToken = document.querySelector('input[name="csrfmiddlewaretoken"]').value;
            const response = await fetch('/app/ai/generate/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/x-www-form-urlencoded',
                    'X-CSRFToken': csrfToken
                },
                body: `prompt=${encodeURIComponent(prompt)}`
            });

            if (!response.ok) {
                throw new Error('이미지 생성에 실패했습니다.');
            }

            const data = await response.json();

            window.location.href = `/app/create/?${new URLSearchParams({
                image_url: data.image_url,
                generated_prompt: data.generated_prompt,
                original_prompt: prompt
            }).toString()}`;

        } catch (error) {
            alert(error.message);
            console.error('Error:', error);
        } finally {
            generateBtn.disabled = false;
            generateBtn.innerHTML = originalText;
        }
    }

    generateBtn.addEventListener('click', generateImage);

    searchInput.addEventListener('keypress', function (e) {
        if (e.key === 'Enter') {
            e.preventDefault();
            generateImage();
        }
    });
});