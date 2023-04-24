
include ../../etc/Makefile-docker

REG_HOSTNAME ?= regdock

PD ?= files/etc/private.d
CCD ?= /etc/containers/certs.d

CERT_TARGET := files/etc/private.d/$(REG_HOSTNAME).crt
KEY_TARGET := files/etc/private.d/$(REG_HOSTNAME).key
HTP_TARGET := files/etc/private.d/htpasswd

# ---------- custom targets

all: prep docker-all


# ----- prep

prep: $(CERT_TARGET) $(KEY_TARGET) $(HTP_TARGET)

$(KEY_TARGET) $(CERT_TARGET): ../../private.d/cert-settings
	mkdir -p $(PD)
	@if [[ -f $@ ]]; then printf "\n$(RED)ERROR $(RESET) dont want to overwrite $(KEY_TARGET), although ../../private.d/cert-settings apears to be more recent.\nPlease manually remove $@, if it really is time to generate a new key,\nor run 'touch $@' to keep your current keys and move on.\n\n"; exit 2; fi
	source ../../private.d/cert-settings && \
	  openssl req -x509 -newkey rsa:4096 -days $$DAYS \
	    -keyout $(KEY_TARGET) -out $(CERT_TARGET) -nodes \
	    -subj "$${SUBJECT}/CN=$(REG_HOSTNAME)/emailAddress=$${EMAIL}" \
	    -addext "subjectAltName = DNS:$(REG_HOSTNAME)"
	chmod go+r $(CERT_TARGET)
	chmod go-r $(KEY_TARGET)
	@printf "\n$(YELLOW)$(CERT_TARGET) needs to be copied to $(CCD)/... in order to work$(RESET)\n"
	@read -p "Use sudo to do that for you now? " p && \
          if [[ "$$p" == "y"* ]]; then \
            sudo install --backup --compare -D -o root -g root --mode 644 $(CERT_TARGET) $(CCD)/$(REG_HOSTNAME):5443/$(REG_HOSTNAME).crt && \
            sudo install --backup --compare -D -o root -g root --mode 644 $(CERT_TARGET) $(CCD)/$(REG_HOSTNAME):5444/$(REG_HOSTNAME).crt && \
            @printf "\n$(GREEN)copy done $(RESET).\n$(YELLOW)You'll need to copy the $(CERT_TARGET) to any other hosts that intend to use this repo in TLS mode.$(RESET)\n"; \
	  fi

$(HTP_TARGET):
	@echo "creating new username / password for the locked-down flavor of the registry"
	@read -p "username to create for registry use: " username && \
          read -s -p "password: " passwd && \
          $$DOCKER_EXEC run -ti docker.io/httpd:2 htpasswd -Bbn $$username $$passwd > $@
	@echo ""


# ---------- pass-throughs

comp:  # n/a
clean: docker-clean
install: docker-install
test: docker-test
uninstall: docker-uninstall
update: docker-update
