function initializePasswordToggle() {
  // Find all password input fields
  const passwordInputs = document.querySelectorAll('input[type="password"]');

  passwordInputs.forEach((input) => {
    // Skip if already initialized
    if (input.dataset.toggleInitialized === 'true') {
      return;
    }

    // Create wrapper div if it doesn't exist
    let wrapper = input.parentElement;
    if (!wrapper.classList.contains('relative')) {
      const newWrapper = document.createElement('div');
      newWrapper.className = 'relative';
      input.parentNode.insertBefore(newWrapper, input);
      newWrapper.appendChild(input);
      wrapper = newWrapper;
    }

    // Create eye icon button
    const toggleButton = document.createElement('button');
    toggleButton.type = 'button';
    toggleButton.className =
      'absolute right-4 top-1/2 -translate-y-1/2 text-gray-500 hover:text-gray-700 focus:outline-none';
    toggleButton.setAttribute('aria-label', 'Toggle password visibility');

    const eyeIcon = document.createElement('i');
    eyeIcon.className = 'fa-solid fa-eye';
    toggleButton.appendChild(eyeIcon);

    // Add click handler
    toggleButton.addEventListener('click', function () {
      const type =
        input.getAttribute('type') === 'password' ? 'text' : 'password';
      input.setAttribute('type', type);

      // Toggle icon
      if (type === 'text') {
        eyeIcon.classList.remove('fa-eye');
        eyeIcon.classList.add('fa-eye-slash');
      } else {
        eyeIcon.classList.remove('fa-eye-slash');
        eyeIcon.classList.add('fa-eye');
      }
    });

    // Insert button after input
    wrapper.appendChild(toggleButton);

    // Mark as initialized
    input.dataset.toggleInitialized = 'true';
  });
}

// Initialize on DOMContentLoaded
document.addEventListener('DOMContentLoaded', initializePasswordToggle);

// Initialize on Turbo render (for Turbo framework)
document.addEventListener('turbo:render', initializePasswordToggle);
document.addEventListener('turbo:load', initializePasswordToggle);
