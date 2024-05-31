
; =================================================================
; EMACS EXTENSION MODULE

(load "~/.ees")
(global-unset-key "\C-c")
(global-set-key "\C-c" 'ken-emacs-extension)


; ================================================================= 
; SET UP PREFERENCES:

(put 'downcase-region 'disabled nil)
(put 'eval-expression 'disabled nil)
(put 'narrow-to-region 'disabled nil)
(put 'set-goal-column 'disabled nil)
(put 'scroll-left 'disabled nil)
(put 'upcase-region 'disabled nil)

(defun yes-or-no-p(x) (y-or-n-p x))
(defconst backup-directory "~/tmp/baks" "*The directory to put backup files in.")
(defun make-backup-file-name (file) "Create the non-numeric backup file name for FILE."
  (if (not (file-exists-p backup-directory)) (shell-command (concat "mkdir -p " backup-directory)))
  (concat backup-directory "/" (file-name-nondirectory file) "~")
)
(set 'inhibit-local-variables t)
(setq backup-by-copying t)
(setq default-major-mode 'text-mode)
(setq inhibit-startup-screen t)
(setq make-backup-files t)
(setq server-temp-file-regexp "tmp.*")
(setq shell-file-name "/bin/bash")
(setq trim-versions-without-asking nil)
(setq-default fill-column 78)

; ---- dired
; use ^u-s to change dired "switches" at runtime
(setq dired-listing-switches "-Bhl1v  --group-directories-first")
(setq image-dired-thumb-size 200)

; --- calc prefs
(setq calc-display-trail nil)
(global-set-key "\C-x#" 'calc-dispatch)


; ================================================================= 
; MODE HOOKS

(add-hook 'dired-mode-hook
          (lambda () (local-set-key (kbd "M-<up>") #'dired-up-directory)))

(add-hook 'html-mode-hook
      (lambda ()
         (setq-default indent-tabs-mode nil)
         (auto-fill-mode -1)
         (setq truncate-lines 0)))
      
(add-hook 'python-mode-hook
      (lambda ()
        (setq indent-tabs-mode f)
        (setq tab-width 4)
        (setq python-indent-offset 4)))

(defun shell-mode-hook ()
 (local-set-key "\C-c" 'ken-emacs-extension)
 (make-local-variable 'scroll-step)
 (setq scroll-step 5))

(defun ken-text-mode-hook ()
  (turn-on-auto-fill)
  (abbrev-mode 1)
)
(setq text-mode-hook 'ken-text-mode-hook)
(ken-text-mode-hook)                    ;and run it once now.


; =================================================================
; ASSIGN NEW KEYBINDINGS

; == define function keys for built-in commands:
(global-set-key [f1] 'other-window)   ;F1
(global-set-key [f3] 'find-file-other-window) ;F3
(global-set-key [f5] 'isearch-forward) ;F5
(global-set-key [f6] 'isearch-forward-regexp) ;F6
(global-set-key [f7] 'isearch-backward) ;F7
(global-set-key [f8] 'isearch-backward-regexp) ;F8
(global-set-key [f9] 'find-file) ;F9
(global-set-key [f10] 'save-buffer) ;F10

; == define function keys for new functions:
(global-set-key [f2] 'ken-switch-to-buffer) ;F2
(global-set-key [f4] 'ken-switch-to-buffer-other-window) ;F4
(global-set-key [f11] 'ken-kill-this-buffer) ;F11

;;;; old control-key based function key assignments - DEPRECATED
;;;; == define function keys for built-in commands:
;;;;(global-set-key "\eOP" 'other-window)   ;F1
;;;;(global-set-key "\eOR" 'find-file-other-window) ;F3
;;;;(global-set-key "\eOT" 'isearch-forward) ;F5
;;;;(global-set-key "\eOU" 'isearch-forward-regexp) ;F6
;;;;(global-set-key "\eOV" 'isearch-backward) ;F7
;;;;(global-set-key "\eOW" 'isearch-backward-regexp) ;F8
;;;;(global-set-key "\eOX" 'find-file) ;F9
;;;;(global-set-key "\eOY" 'save-buffer) ;F10

;;;; == define function keys for new functions:
;;;;(global-set-key "\eOQ" 'ken-switch-to-buffer) ;F2
;;;;(global-set-key "\eOS" 'ken-switch-to-buffer-other-window) ;F4
;;;;(global-set-key "\eOZ" 'ken-kill-this-buffer) ;F11


; == define short-cut keys for built-in commands:
(global-set-key "\e "      'lisp-complete-symbol) ;built-in's
(global-set-key "\C-x\C-g" 'goto-line)
(global-set-key "\C-x\\"   'what-line)
(global-set-key "\e\t"     'indent-region)
(global-set-key "\C-z"     'zap-to-char)
(global-set-key "\e\C-z"   'suspend-emacs)
(global-set-key "\e]"      'forward-paragraph)
(global-set-key "\e["      'backward-paragraph)
(global-set-key "\C-xF"    'find-name-dired)
(global-set-key "\C-xG"    'find-grep-dired)
(global-set-key "\C-\\"    'compile)

; == define short-cuts keys for new functions:
(global-set-key "\C-]" 'vi-find-matching-paren) ;new functions
(global-set-key "\C-k" 'zap-line)
;(global-set-key "\C-\n" 'special-eol)
(global-set-key "\C-f" 'ken-special-forward-char)

; --------------------------------------------------
; define the new functions called from above

; -- function keys:

(defun ken-switch-to-buffer ()          ;f2
  "Toggle current buffer with previous one."
  (interactive)
  (switch-to-buffer (other-buffer)))

(defun ken-switch-to-buffer-other-window () ;f4
  "Toggle other window's buffer with previous one."
  (interactive)
  (switch-to-buffer-other-window (other-buffer)))

(defun ken-kill-this-buffer ()          ;f11
  "Kens kill the current buffer"
  (interactive)
  (kill-buffer (buffer-name)))


; -- short-cut keys:

(defun vi-find-matching-paren ()
  "Kens copy of vi-parren matching program"
  (interactive)
  (cond ((looking-at "[[({]") (forward-sexp 1) (backward-char 1))
        ((looking-at "[])}]") (forward-char 1) (backward-sexp 1))
        (t (search-backward "{"))))

(defun zap-line ()
  "Kens line killer"
  (interactive)
  (beginning-of-line)
  (kill-line 1))

(defun special-eol ()
  "Kens end of line processor: eol => next & indent, else kill to eol"
  (interactive)
  (cond ((eolp) (newline-and-indent))
        (t (kill-line))))


(setq ken-sep "[        ]+")            ;default field seperator

(defun ken-special-forward-char (&optional arg)
  "If ARG given, and positive move to _field_ ARG.  
   If negative, go forwad ARG chars, else go forward one."
  (interactive "p")
  (if (< arg 2)
      (forward-char (abs arg))          ;run the old routine if no arg
    (ken-repeat (1- arg) '(lambda () (re-search-forward ken-sep nil 't)))
) )

; enable gpg passphrase challene in minibuffer
(setq epg-gpg-program "usr/bin/gpg2")
(require 'epa-file)
(epa-file-enable)
(setq epa-file-select-keys nil)
(setq epa-pinentry-mode 'loopback)

; ================================================================= 
; Themes

;; (add-to-list 'custom-theme-load-path "~/.emacs.d/themes/")

;; (load-theme 'zenburn t)
(load-theme 'modus-vivendi t)


; ================================================================= 
; emacs maintained options (x gui version)

(custom-set-variables
 ;; custom-set-variables was added by Custom.
 ;; If you edit it by hand, you could mess it up, so be careful.
 ;; Your init file should contain only one such instance.
 ;; If there is more than one, they won't work right.
 '(custom-safe-themes
   '("b9e9ba5aeedcc5ba8be99f1cc9301f6679912910ff92fdf7980929c2fc83ab4d" "84d2f9eeb3f82d619ca4bfffe5f157282f4779732f48a5ac1484d94d5ff5b279" default))
 '(tool-bar-mode nil))
(custom-set-faces
 ;; custom-set-faces was added by Custom.
 ;; If you edit it by hand, you could mess it up, so be careful.
 ;; Your init file should contain only one such instance.
 ;; If there is more than one, they won't work right.
 )

; ================================================================= 

(load "server")
(unless (server-running-p) (server-start))

; ----------

(find-file "~")
(message "ready...")
