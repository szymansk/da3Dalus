#init:
#	pip install -r requirements.txt

#test:
#	py.test tests

doc:
	docker run -it --rm -v ./docs/:/documents/ uwebarthel/asciidoctor asciidoctor -o html/documentation.html -r asciidoctor-diagram documentation.adoc

.PHONY: init test
