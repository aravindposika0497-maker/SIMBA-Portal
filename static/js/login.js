(() => {
  const button = document.getElementById('togglePassword');
  const input = document.getElementById('password');
  if (button && input) button.addEventListener('click', () => {
    const show = input.type === 'password';
    input.type = show ? 'text' : 'password';
    button.textContent = show ? 'Hide' : 'Show';
    button.setAttribute('aria-label', show ? 'Hide password' : 'Show password');
  });
})();
