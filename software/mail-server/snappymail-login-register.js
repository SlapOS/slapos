(rl => {
  if (rl) {
    const showInfoDialog = (title, message) => {
      let dialog = document.getElementById('plugin-info-dialog');
      if (!dialog) {
        dialog = Element.fromHTML(
          '<dialog id="plugin-info-dialog">' +
          '<header><a class="close" href="#">×</a><h3></h3></header>' +
          '<div class="modal-body"></div>' +
          '<footer><button class="btn">OK</button></footer>' +
          '</dialog>'
        );
        dialog.querySelector('.close').addEventListener('click', e => {
          e.preventDefault();
          dialog.classList.remove('animate');
          setTimeout(() => dialog.close(), 200);
        });
        dialog.querySelector('footer .btn').addEventListener('click', () => {
          dialog.classList.remove('animate');
          setTimeout(() => dialog.close(), 200);
        });
        document.getElementById('rl-popups').append(dialog);
      }
      dialog.querySelector('header h3').textContent = title;
      dialog.querySelector('.modal-body').textContent = message;
      dialog.showModal();
      requestAnimationFrame(() => {
        dialog.offsetHeight; // force reflow
        dialog.classList.add('animate');
      });
    };

    addEventListener('rl-view-model', e => {
      if (e.detail && 'Login' === e.detail.viewModelTemplateID) {
        const container = e.detail.viewModelDom.querySelector('#plugin-Login-BottomControlGroup'),
          forgot = 'LOGIN/LABEL_FORGOT_PASSWORD',
          register = 'LOGIN/LABEL_REGISTRATION';
        if (container) {
          let html = '';
          html = html + '<p class="forgot-link">'
            + '<a href="#" class="g-ui-link" data-i18n="'+forgot+'">'+rl.i18n(forgot)+'</a>'
            + '</p>';
          html = html + '<p class="registration-link">'
            + '<a href="#" class="g-ui-link" data-i18n="'+register+'">'+rl.i18n(register)+'</a>'
            + '</p>';
          container.append(Element.fromHTML('<div class="controls clearfix">' + html + '</div>'));

          container.querySelector('.forgot-link a')?.addEventListener('click', e => {
            e.preventDefault();
            // to reset their password the user should update the shared instance's params with a "reset-token" param set to something and that can be used
            showInfoDialog(
              rl.i18n(forgot),
              'To reset your password, add a "reset-token" parameter to your account\'s shared instance parameters and set it to any value. A password reset URL will be returned to you.'
            );
          });

          container.querySelector('.registration-link a')?.addEventListener('click', e => {
            e.preventDefault();
            showInfoDialog(
              rl.i18n(register),
              'To register a new account, create a new shared instance with your desired email address as the "address" parameter. A registration URL will be returned to you.'
            );
          });
        }
      }
    });
  }

})(window.rl);
