# regtest.py

import re
import markdown

#exp = r'(~~)([^~]*(~[^~]+)+)(~~)'
exp = r'(~~)(.*?)(~~)'
#exp = r'(a)(.*)(c)'

test1 = 'foo abc bar'
test2 = 'foo a~bc bar'
test3 = 'foo a~~bc bar'
test4 = 'foo a~~b~~c bar'
test5 = 'foo a~~b~c~~d bar'
test6 = 'foo a~~b~c~~d~~e bar'
test7 = 'foo a~~b~c~~d~~e b~~ar'
test8 = 'foo a~~b~c~~ ^^e b^^ar'

def test(text):
    m = re.search(exp, text)
    if m is None:
        print(text, m)
    else:
        print(text, m, m.group(2))

for text in test1, test2, test3, test4, test5, test6, test7, test8:
    test(text)

class DelExtension(markdown.extensions.Extension):
    def extendMarkdown(self, md):
        md.inlinePatterns.register(markdown.inlinepatterns.SimpleTagInlineProcessor(r'(~~)(.*?)(~~)',
                                                                                    'del'),
                                  'del', 105)

class InsExtension(markdown.extensions.Extension):
    def extendMarkdown(self, md):
        md.inlinePatterns.register(markdown.inlinepatterns.SimpleTagInlineProcessor(r'(\^\^)(.*?)(\^\^)',
                                                                                    'ins'),
                                  'ins', 106)

md = markdown.Markdown(extensions=[DelExtension(), InsExtension()])

for text in test1, test2, test3, test4, test5, test6, test7, test8:
    print("md", text, md.convert(text))  # also md.convertFile
