
; =================================================================
; EMACS EXTENSION SYSTEM (EES) (c) 1992 Ken Stillson 
;
; This program is distributed under the FSF's GPL (Gnu Public License)
;
; See the EMACS documentation for information concerning distribution,
; modification, warantee (lack thereof), etc.
;

; give okay message now so any error messages overlay it...
(message "Emacs extension system loaded.")


; --------------------------------------------------
; GENERAL LISP LIBRARY STUFF

; == general tools:

(defun ken-print (x)			;print x into text
  (insert (prin1-to-string x)))

(defun rs () (min (point) (mark)))	;region start
(defun re () (max (point) (mark)))	;region end

(defun ken-what-line ()			;return line number
  (save-excursion
    (beginning-of-line)
    (1+ (count-lines 1 (point))))
)

(defun ken-repeat (count func)		;repeat func count times
  (setq cntr 0)
  (while (< cntr count) (progn
    (funcall func)
    (setq cntr (1+ cntr)) )
) )

(defun ken-max-list (list)		;find max # in list
  (setq max-val (car list))
  (while (setq list (cdr list))
     (setq max-val (max max-val (car list)))
  )
  max-val)

(defun zero (x) 0)			;return zeros

(defun abs (number)			;return absolute val of number
  (if (> number 0) number
    (- 0 number)))

(defun ken-just-region (func)		;narrow, do func, widen
  (narrow-to-region (mark) (point))
  (beginning-of-buffer)
  (funcall func)
  (widen))

(defun ken-replace (old new)
  "Replace OLD string with NEW, quickly."
  (interactive "sOld:\nsNew:\n")
  (buffer-disable-undo (buffer-name))
  (while (search-forward old nil t)
    (replace-match new nil t))
  (buffer-enable-undo (buffer-name))
)


; --------------------------------------------------
; tools dealing with field/region line widths:
; (library for the field alignment system (which follows)


; return a list of line lengths of lines in p1->p2
;
(defun ken-length-list-region (p1 p2)
  (setq len-list nil)
  (save-excursion
    (goto-char p1)
    (while (<= (point) p2)
      (progn  
	(end-of-line)
	(setq len-list (cons (current-column) len-list))
	(next-line 1)
  )	) )
  (reverse len-list))


; find a list of field beginning columns, for every field in a line
;
(defun ken-get-line-field-list (line)
  (setq field-list nil)
  (save-excursion
    (goto-line line)
    (beginning-of-line)
    (if (looking-at "[ 	]") (re-search-forward ken-sep nil 't))
    (while (= (ken-what-line) line)
      (setq field-list (cons (current-column) field-list))
      (re-search-forward ken-sep nil 't)
 ) ) 
  (reverse field-list))


; find a list of field beginning columns, for a given field number,
; over a region of lines
;
(defun ken-get-field-list (p1 p2 field)
  ; this effectivly gets the start of column #2:
  (setq list (ken-length-list-region-field p1 p2 0))
  (if (< field 2) 
      (mapcar 'zero list)		; can't easily do < column #2
    (progn
      (setq cntr 2)
      (while (< cntr field) (progn
	(setq list (ken-length-list-region-field-list p1 p2 list))
	(setq cntr (1+ cntr)) )
    ) )
    list ))


; in region P1->P2, find the column of the first instance of ken-sep after
; the coorisponding element of F1, and add it to a list, which is
; returned.  f1 is the for each line.
;
(defun ken-length-list-region-field (p1 p2 f1)
  (setq len-list nil)
  (save-excursion
    (goto-char p1)
    (while (<= (point) p2)
      (progn  
	(move-to-column f1)
	(setq line (ken-what-line))
	(re-search-forward ken-sep nil 't)
	(if (> (ken-what-line) line) 
	    (progn (goto-line line) (end-of-line)))
	(setq len-list (cons (current-column) len-list))
	(next-line 1)
  )	) )
  (reverse len-list))


; in region P1->P2, find the column of the first instance of ken-sep after
; the coorisponding element of F1, and add it to a list, which is
; returned.  f1 is a list, one element for each line.
; (actually, p2 is ignored- number of lines is determined by (length f1-list))
;
(defun ken-length-list-region-field-list (p1 p2 f1-list)
  (setq len-list nil)
  (save-excursion
    (setq kenmark (point))
    (goto-char p1)
    (while f1-list
      (progn
	(move-to-column (car f1-list))
	(setq f1-list (cdr f1-list))
	(setq line (ken-what-line))
	(re-search-forward ken-sep nil 't)
	(if (> (ken-what-line) line) 
	    (progn (goto-line line) (end-of-line)))
	(setq len-list (cons (current-column) len-list))
	(next-line 1)
  )	) )
  (reverse len-list))


; --------------------------------------------------
; == column alignment system  (field tidying)

; in region P1->P2, with fields starting at column F1 and ending at the
; first subiquent ken-sep (a regexp), find the widest field, and expand all
; the other fields to the same length, thus tiding the left edge of the
; field on the right, and the left edge of the field on the left.
;
(defun ken-tidy-fixed-field (p1 p2 f1)
  (setq len-list (ken-length-list-region-field p1 p2 f1))
  (setq max-val (ken-max-list len-list))
  (goto-char p1)
  (while len-list
    (progn
      (setq len (car len-list))
      (setq len-list (cdr len-list))
      (move-to-column len)
      (insert-char 32 (- max-val len))
      (next-line 1) ) ) )


; in region P1->P2, with fields starting at column F1 and ending at the
; first subiquent ken-sep (a regexp), find the widest field, and expand all
; the other fields to the same length, thus tiding the left edge of the
; field on the right, and the left edge of the field on the left.
; f1-list is a list, one field start per line within the region.
; (actually, p2 is ignored- number of lines is determined by (length f1-list))
;
(defun ken-tidy-field-list (p1 p2 f1-list)
  (setq len-list (ken-length-list-region-field-list p1 p2 f1-list))
  (setq max-val (ken-max-list len-list))
  (goto-char p1)
  (while len-list
    (progn
      (setq len (car len-list))
      (setq len-list (cdr len-list))
      (move-to-column len)
      (insert-char 32 (- max-val len))
      (next-line 1) ) ) )


; tidy's a given field number
;
(defun ken-tidy-field (p1 p2 field)
  "Given field number, tidy it within the region."
  (interactive "r\np")
  (setq list (ken-get-field-list p1 p2 field))
(message (format "%d,%d,%d." p1 p2 field))
  (ken-tidy-field-list p1 p2 list))

; --------------------------------------------------
; primary entry point functions for EES

; == movement 

(defun kens-tab-match ()
  "Kens match indentation of previous line"
  (interactive)
  (set-goal-column (current-column))
  (previous-line 1)
  (forward-word 1)
  (backward-word 1)
  (setq col (current-column))
  (next-line 1)
  (indent-to-column col)
  (set-goal-column 0))

(defun ken-move-end-column ()
  "Move to bottom of current column (leave mark)"
  (interactive)
  (set-mark-command nil)
  (setq col (current-column))
  (forward-paragraph 1)
  (backward-word 1)
  (move-to-column col))

(defun ken-move-to-end (arg)
  "Move current line to end of file"
  (interactive)
  (beginning-of-line)
  (set-mark-command nil)
  (next-line 1)
  (if (= arg 0) 
      (kill-region (mark) (point))
      (copy-region-as-kill (mark) (point))
  )
  (end-of-buffer)
  (yank)
  (set-mark-command 1)
  (set-mark-command 1)
  (set-mark-command 1))


; == change text

(defun ken-copy-line ()
  "copy current line into kill ring"
  (interactive)
  (beginning-of-line)
  (set-mark-command nil)
  (setq kenmark (point))
  (next-line 1)
  (copy-region-as-kill kenmark (point))) 

(defun ken-zap ()
  "eat chars up to but not includnig given char"
  (interactive)
  (setq c (read-char))
  (zap-to-char 1 c)
  (insert c)
  (backward-char 1)
)

(defun ken-eat-spaces ()
  "eat spaces and tabs until real character"
  (interactive)
  (setq kenmark (point))
  (re-search-forward "[0-z]" nil t)
  (kill-region kenmark (1- (point)))
  (backward-char 1))

(defun ken-convert-comment ()
  "convert line to/from a c style comment"
  (interactive)
  (save-excursion
    (beginning-of-line)
    (if (looking-at " */\\*")
	(progn
 	  (zap-to-char 1 42)
  	  (delete-char 2)
 	  (end-of-line)
	  (delete-char -3)
	  )
      (progn
	(insert "/* ")
	(end-of-line)
	(insert " */") ) ) ) )


(defun ken-mark-field ()
  "Kens mark current column to eof"
  (interactive)
  (set-mark-command nil)
  (forward-word 1)
  (forward-char 1)
  (setq col (current-column))
  (goto-char (point-max))
  (previous-line 1)
  (move-to-column col))

(defun ken-move-to-column-region-max ()
  (ken-move-to-column-force 
   (ken-max-list (ken-length-list-region (rs) (re)))))


(setq old-r0 0)				;mark no narrowing in progress

(defun ken-narrow-to-rectangle ()
  "Kens narrow edit to rectangle procedure"
  (interactive)
  (setq old-r0 (mark))			;remember orig rectangle
  (setq old-r1 (point))
  (copy-rectangle-to-register 114 (rs) (re) nil) ;grab copy
  (end-of-buffer)
  (insert-register 114)			;lay copy here
  (setq new-r0 (point))			;remember new rectangle
  (exchange-point-and-mark)
  (setq new-width (current-column))
  (exchange-point-and-mark)
  (narrow-to-region (point) (mark)))

(defun ken-move-to-column-force (column) ;taken from picture.el
  "Move to column COLUMN in current line.
Differs from move-to-column in that it creates or modifies whitespace
if necessary to attain exactly the specified column."
  (move-to-column column)
  (let ((col (current-column)))
    (if (< col column)
	(indent-to column)
      (if (and (/= col column)
	       (= (preceding-char) ?\t))
	  (let (indent-tabs-mode)
	    (delete-char -1)
            (indent-to col)
            (move-to-column column))))))

(defun ken-widen-from-rectangle ()
  "Kens undo narrow to rectangle.
     (Use ^x-w to leave extra copy at bottom of document.)"
  (interactive)
  (if (= old-r0 0)
	(message "No rectangle narrowing active.")
    (progn
      (end-of-buffer)
      (ken-move-to-column-force new-width)
      (copy-rectangle-to-register 114 new-r0 (point) 'T) ;grab new one
      (widen)
      (kill-region new-r0 (point-max))	;remove blank space
      (set-mark old-r1)			;mark old version
      (goto-char old-r0)
      (kill-rectangle (point) (mark))	;kill old version
      (insert-register 114)		;insert new version
      (setq old-r0 0)			;mark no longer narrowed
)))

(defun ken-shell-command-on-rectangle (command)
  "Execute string COMMAND in shell with rectangle as input.
   Place result into register A."
  (interactive "sShell command on rectangle: \n")
  (ken-narrow-to-rectangle)
  (shell-command-on-region (point) (mark) command 't)
  (ken-move-to-column-region-max)
  (copy-rectangle-to-register 97 new-r0 (point) 'T) ;grab answer
  (widen)
  (kill-region new-r0 (point-max))	;remove blank space
  (set-mark old-r1)			;mark old version
  (goto-char old-r0)
  (message "Answer place into rectangular register A."))

(defun ken-move-region-to-k ()
  "Kens move region to append register k"
  (interactive)
  (append-to-register 107 (point) (mark) 'T))

(defun ken-move-line-to-k ()
  "Kens move current line to append register k"
  (interactive)
  (save-excursion
    (beginning-of-line)
    (set-mark-command nil)
    (next-line 1)
    (ken-move-region-to-k)))

; == control windows

(defun ken-kill-window ()
  "Kens kill buffer and close window"
  (interactive)
  (kill-buffer (buffer-name))
  (delete-window))

(defun ken-kill-other-window ()
  "Kens kill other window's buffer and close window"
  (interactive)
  (other-window 1)
  (kill-buffer (buffer-name))
  (delete-window))

(defun ken-save-kill ()
  "save and kill currnet buffer"
  (interactive)
  (command-execute 'save-buffer)
  (kill-buffer (buffer-name)))

(defun ken-cmnd-other-window (return)
  "Do command in other window"
  (interactive)
  (setq ken-temp (read-key-sequence "Cmd other win: "))
  (other-window 1)
  (execute-kbd-macro ken-temp nil)
  (if return (other-window 1)))


; == OTHER

(defun smart-compile ()
  "Kens smart compiler"
  (interactive)
  (setq cmnd "make -f ~/mine/make.all prog=")
  (setq cmnd (concat cmnd
	      (substring (buffer-name) 0 (string-match "\\." (buffer-name)))))
  (compile cmnd))

(defun smart-debug ()
  "Kens smart compiler"
  (interactive)
  (setq file (substring (buffer-name) 0 (string-match "\\." (buffer-name))))
  (other-window 1)
  (gdb file))

(defun ken-repeat-macro-paragraph ()
  "Kens repeat macro over current paragraph"
  (if defining-kbd-macro (end-kbd-macro))
  (save-excursion
    (setq kenmark (point))
    (forward-paragraph 1)
    (setq kenmark0 (ken-what-line))
  )
  (while (< (ken-what-line) kenmark0)
    (call-last-kbd-macro)))

; == REGION

(defun ken-copy-region-other-window ()
  "Copy current region to the other window"
  (save-excursion
    (copy-region-as-kill (mark) (point))
    (other-window 1)
    (yank)
    (other-window -1)))

(defun ken-move-region-other-window ()
  "Move current region to the other window"
  (kill-region (mark) (point))
  (other-window 1)
  (yank))

(defun ken-region-delete-all-but-first-word ()
  (ken-just-region
   '(lambda () 
      (replace-regexp "[ 	].*$" ""))))

(defun ken-underline-line (chr)
  "Repeat current line in underlines"
  (interactive "p")
  (set-mark-command nil)
  (beginning-of-line)
  (copy-region-as-kill (rs) (re))
  (next-line 1)
  (open-line 1)
  (yank)
  (narrow-to-region (rs) (re))
  (beginning-of-line)
  (replace-regexp "[^ 	]" "-")
  (widen))  


; --------------------------------------------------
; Define the menu

(defun ken-emacs-extension (&optional arg)
"Kens ^C Emacs Extension System: (EES)

   MOVEMENT                            OTHER
    TAB - match above indentation         \\ - Set tab-stops to fields
     ^n - move to bottom of column        ! - run shell
     ^v - scroll both windows             C - compile, ^d - debug
                                          a - toggle auto-fill mode
   CONTROL BUFFERS / WINDOWS              W - eval whole buffer
      ^ - expand window vert            ESC - repeat kbd macro on para
      > - expand window horiz
      0 - kill & close this buffer     REGION
      4 - kill & close other buffer       1 - delete all but 1st word
      f - toggle auto-fill mode           @ - duplicate region      
      k - save & kill current buffer      # - number lines in region
      o - cmnd other win (^o to stay)     - - underline current line       
      N - change buffer & file name       < - sort region (by line)        
      t - toggle truncate lines          ^e - eval region
      v - toggle version control          A - Align column ARG
                                         ^c - copy [^m-move] to next window
   CHANGE TEXT                            T - kill trailing spaces
      2 - duplcate line		         ^w - write region to file
      e - move line to end of file
      E - copy line to end of file     FIELD / RECTANGLE
      l - copy line to kill buffer        c - mark field to eof
     ^r - replace regexp                  M - move col to max width
     ^s - replace string                  m - move recrange to R
      z - zap to (not including) char     n - Narrow to rectangle                         
     BS - eat spaces                      w - widen from rectangle
      ; - cvt line to/from comment        | - filter on rectangle 
      / - move region to register k       
      . - move line to register k
"
  (interactive "p")
  (setq ken-arg arg)
  (setq func (read-char))
  (cond

; == MOVEMENT
   ( (= func 9) (kens-tab-match))                 ;\t 
   ( (= func 14) (ken-move-end-column))           ;^n
   ( (= func 22) (scroll-up nil)(scroll-other-window nil)) ;^v
   ( (= func 101) (ken-move-to-end 0))		  ;e
   ( (= func 69) (ken-move-to-end 1))		  ;E

; == CHANGE TEXT
   ( (= func 50) (zap-line)(yank)(yank)(previous-line 1)) ;2
   ( (= func 108) (ken-copy-line))   	          ;l
   ( (= func 18) (command-execute 'replace-regexp)) ;^r
   ( (= func 19) (command-execute 'ken-replace)) ;^s
   ( (= func 114) (command-execute 'query-replace-regexp)) ;r
   ( (= func 115) (command-execute 'query-replace)) ;s
   ( (= func 122) (ken-zap))                      ;z
   ( (= func 127) (ken-eat-spaces))	          ;BS
   ( (= func 59) (ken-convert-comment))	          ;;
   ( (= func 47) (ken-move-region-to-k))          ;/
   ( (= func 46) (ken-move-line-to-k))            ;.

; == FIELD/RECTANGLE
   ( (= func 99) (ken-mark-field))                ;c
   ( (= func 77) (ken-move-to-column-region-max)) ;M
   ( (= func 109) (copy-rectangle-to-register 114 (rs) (re) 'T)) ;m
   ( (= func 110) (ken-narrow-to-rectangle))       ;n
   ( (= func 119) (ken-widen-from-rectangle))      ;w
   ( (= func 124) (command-execute 'ken-shell-command-on-rectangle)) ;|
   ; undocumented:
   ( (= func 82) (copy-rectangle-to-register 114 (rs) (re) 'T)) ;R

; == CONTROL
   ( (= func 94) (enlarge-window (if (= arg 1) 6 arg))) ;^
   ( (= func 62) (enlarge-window (if (= arg 1) 6 arg) 't )) ;>
   ( (= func 48) (ken-kill-window))               ;0
   ( (= func 52) (ken-kill-other-window))	  ;4
   ( (= func 102) (command-execute 'auto-fill-mode)) ;f
   ( (= func 107) (ken-save-kill))   		  ;k
   ( (= func 111) (ken-cmnd-other-window t))      ;o
   ( (= func 15) (ken-cmnd-other-window nil))     ;^o
   ( (= func 78) (command-execute 'set-visited-file-name))  ;N 
   ( (= func 116) (setq truncate-lines (not truncate-lines)) ;t
                  (auto-fill-mode (if truncate-lines 0 1))
                  (recenter))
   ( (= func 118) (make-local-variable 'version-control) ;v
                  (setq version-control (not version-control))
		  (message "Version control is: %s" version-control))

; == OTHER
   ( (= func 61) (server-edit))		;= (undocumetned)
   ( (= func 92) (setq tab-stop-list 
		       (ken-get-line-field-list (ken-what-line)))) ;\
   ( (= func 33) (shell))		          ;!
   ( (= func 67) (smart-compile))		  ;C
   ( (= func 4) (smart-debug))			  ;^d
   ( (= func 97) (command-execute 'auto-fill-mode)) ;a
   ( (= func 73) (command-execute 'ispell-buffer));I
   ( (= func 113) (print (read-char)))		  ;q 
   ( (= func 87) (eval-current-buffer)(message "ok")) ;W
   ( (= func 27) (ken-repeat-macro-paragraph))    ;ESC

; == REGION
   ( (= func 65) (ken-tidy-field (rs) (re) ken-arg)) ;A
   ( (= func 49) (ken-region-delete-all-but-first-word)) ;1
   ( (= func 64) (copy-region-as-kill (mark) (point))(yank)) ;@
   ( (= func 35) (shell-command-on-region (mark) (point)
		  "cat -n | sed -e 's/^ *//'" t)) ;#
   ( (= func 45) (command-execute 'ken-underline-line)) ;-
   ( (= func 60) (command-execute 'sort-lines))   ;<
   ( (= func 5) (command-execute 'eval-region))   ;^e 
   ( (= func 3) (ken-copy-region-other-window))  ;^c
   ( (= func 13) (ken-move-region-other-window))  ;^c
   ( (= func 71) (command-execute 'occur)) ;G
   ( (= func 84) (ken-just-region '(lambda ()     ;T
		    (replace-regexp "[ 	]+$" ""))))
   ( (= func 105) (command-execute 'ispell-region));i
   ( (= func 23) (command-execute 'write-region ));^w
   ( t (ding) )
))

; finally- set ^c to run the system:

(defun ken ()
  "Activate C-c emacs extension system in local buffer"
  (interactive)
  (local-unset-key "\C-c")
  (local-set-key "\C-c" 'ken-emacs-extension)
)
(ken)

