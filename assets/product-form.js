if (!customElements.get('product-form')) {
  customElements.define(
    'product-form',
    class ProductForm extends HTMLElement {
      constructor() {
        super();

        this.form = this.querySelector('form');
        this.submitButton = this.form?.querySelector(
          '.add-to-cart-button button',
        );

        if (!this.form || !this.submitButton) return;

        const variantInput = this.variantIdInput;
        if (variantInput) variantInput.disabled = false;

        this.submitButtonText = this.submitButton.querySelector('span');
        this.loadingSpinner =
          this.submitButton.querySelector('.loading__spinner') ||
          this.querySelector('.loading__spinner');

        this.cart =
          document.querySelector('cart-notification') ||
          document.querySelector('cart-drawer');
        this.form.addEventListener('submit', this.onSubmitHandler.bind(this));

        if (document.querySelector('cart-drawer')) {
          const inquireTrigger =
            this.submitButton.getAttribute('data-modal-trigger') !==
            'inquire-modal';
          if (inquireTrigger && this.submitButton.matches('[type="submit"]')) {
            this.submitButton.setAttribute('aria-haspopup', 'dialog');
          }
        }

        this.hideErrors = this.dataset.hideErrors === 'true';
        this.isSubmitting = false;
      }

      onSubmitHandler(evt) {
        evt.preventDefault();
        if (
          !this.submitButton ||
          this.isSubmitting ||
          !this.variantIdInput?.value
        )
          return;

        this.isSubmitting = true;
        this.handleErrorMessage();

        if (typeof fetch !== 'function' || typeof fetchConfig !== 'function') {
          this.fallbackToNativeSubmit();
          return;
        }

        const config = fetchConfig('javascript');
        config.headers['X-Requested-With'] = 'XMLHttpRequest';
        delete config.headers['Content-Type'];

        const formData = new FormData(this.form);
        if (this.cart) {
          formData.append(
            'sections',
            this.cart.getSectionsToRender().map((section) => section.id),
          );
          formData.append('sections_url', window.location.pathname);
          this.cart.setActiveElement(document.activeElement);
        }
        config.body = formData;

        fetch(`${routes.cart_add_url}`, config)
          .then((response) => response.json())
          .then((response) => {
            if (response.status) {
              publish(PUB_SUB_EVENTS.cartError, {
                source: 'product-form',
                productVariantId: formData.get('id'),
                errors: response.errors || response.description,
                message: response.message,
              });
              this.handleErrorMessage(response.description);

              const soldOutMessage =
                this.submitButton.querySelector('.sold-out-message');
              if (!soldOutMessage) return;
              this.submitButtonText?.classList.add('hidden');
              soldOutMessage.classList.remove('hidden');
              this.error = true;
              return;
            } else if (!this.cart) {
              window.location = window.routes.cart_url;
              return;
            }

            if (!this.error)
              publish(PUB_SUB_EVENTS.cartUpdate, {
                source: 'product-form',
                productVariantId: formData.get('id'),
                cartData: response,
              });
            this.error = false;
            const quickAddModal = this.closest('quick-add-modal');
            if (quickAddModal) {
              document.body.addEventListener(
                'modalClosed',
                () => {
                  setTimeout(() => {
                    this.cart.renderContents(response);
                  });
                },
                { once: true },
              );
              quickAddModal.hide(true);
            } else {
              this.cart.renderContents(response);
            }
          })
          .catch((e) => {
            console.error(e);
            this.fallbackToNativeSubmit();
          })
          .finally(() => {
            this.isSubmitting = false;
            if (this.cart && this.cart.classList.contains('is-empty'))
              this.cart.classList.remove('is-empty');
          });
      }

      handleErrorMessage(errorMessage = false) {
        this.errorMessageWrapper =
          this.errorMessageWrapper ||
          this.querySelector('.product-form__error-message-wrapper');
        if (!this.errorMessageWrapper) return;
        this.errorMessage =
          this.errorMessage ||
          this.errorMessageWrapper.querySelector(
            '.product-form__error-message',
          );

        this.errorMessageWrapper.toggleAttribute('hidden', !errorMessage);

        if (errorMessage) {
          this.errorMessage.textContent = errorMessage;
        }
      }

      refreshSubmitButton() {
        this.submitButton = this.form?.querySelector(
          '.add-to-cart-button button',
        );
        if (!this.submitButton) return;

        this.submitButtonText = this.submitButton.querySelector('span');
        this.loadingSpinner =
          this.submitButton.querySelector('.loading__spinner') ||
          this.querySelector('.loading__spinner');
      }

      setBuyButtonForVariant(variant, sizeValue = '') {
        this.refreshSubmitButton();
        const button = this.submitButton;
        if (!button || !variant) return;

        const sectionId = this.dataset.sectionId;
        const onSale =
          variant.compare_at_price != null &&
          variant.compare_at_price > variant.price;

        button.removeAttribute('aria-disabled');
        button.classList.remove('loading');

        if (sectionId) {
          button.id = `ProductSubmitButton-${sectionId}`;
        }

        let label = button.querySelector('span.text-15');
        if (!label) {
          label = document.createElement('span');
          label.className = 'text-15';
          button.prepend(label);
        }
        label.classList.remove('hidden');

        if (variant.available) {
          button.type = 'submit';
          button.name = 'add';
          button.removeAttribute('data-modal-trigger');
          button.removeAttribute('data-inquire-size');
          button.removeAttribute('disabled');
          label.textContent = window.variantStrings.addToCart;
          return;
        }

        if (onSale) {
          button.type = 'submit';
          button.name = 'add';
          button.removeAttribute('data-modal-trigger');
          button.removeAttribute('data-inquire-size');
          button.setAttribute('disabled', 'disabled');
          label.textContent = window.variantStrings.inventoryOutOfStock;
          return;
        }

        button.type = 'button';
        button.removeAttribute('name');
        button.removeAttribute('disabled');
        button.setAttribute('data-modal-trigger', 'inquire-modal');
        if (sizeValue) {
          button.setAttribute('data-inquire-size', sizeValue);
        } else {
          button.removeAttribute('data-inquire-size');
        }
        label.textContent = window.variantStrings.inquire;
      }

      toggleSubmitButton(disable = true, text) {
        this.refreshSubmitButton();
        if (!this.submitButton) return;
        const isInquire =
          this.submitButton.getAttribute('data-modal-trigger') ===
          'inquire-modal';

        if (disable) {
          if (isInquire) {
            this.submitButton.removeAttribute('disabled');
            if (text && this.submitButtonText) {
              this.submitButtonText.textContent = text;
            }
          } else {
            this.submitButton.setAttribute('disabled', 'disabled');
            if (text && this.submitButtonText) {
              this.submitButtonText.textContent = text;
            }
          }
        } else {
          this.submitButton.removeAttribute('disabled');
          if (this.submitButtonText) {
            this.submitButtonText.textContent = window.variantStrings.addToCart;
          }
        }
      }

      fallbackToNativeSubmit() {
        if (!this.form) return;

        this.isSubmitting = false;

        HTMLFormElement.prototype.submit.call(this.form);
      }

      get variantIdInput() {
        return this.form.querySelector('[name=id]');
      }
    },
  );
}
