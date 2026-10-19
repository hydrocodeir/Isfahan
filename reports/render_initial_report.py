"""Use the packaged PNG renderer with a native Word conversion on Windows.

The runtime manifest has no bundled LibreOffice for Windows. The canonical
renderer was attempted and reported missing soffice.exe. Word supplies the PDF;
the packaged renderer still performs sizing and Poppler page rasterization.
"""
import importlib.util, os, sys, shutil
from pathlib import Path
root=Path(__file__).resolve().parents[1]
runtime=Path('C:/Users/psh2610/.cache/codex-runtimes/codex-primary-runtime/dependencies')
os.environ['PATH']=str(runtime/'native/poppler/Library/bin')+os.pathsep+os.environ.get('PATH','')
skill=Path('C:/Users/psh2610/.codex/plugins/cache/openai-primary-runtime/documents/26.1007.11041/skills/documents/render_docx.py')
spec=importlib.util.spec_from_file_location('packaged_renderer',skill)
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
out=root/'reports/initial_progress_14050719'
def convert(input_path,user_profile,output_dir,stem,verbose=False):
    target=Path(output_dir)/(stem+'.pdf');shutil.copy2(out/'word_render.pdf',target)
    return str(target),'Native Word PDF conversion; packaged Poppler rasterization'
module.convert_to_pdf=convert
sys.argv=[str(skill),str(out/'گزارش اولیه اقدامات داشبورد انتقال آب ۱ تا ۱۹ مهر ۱۴۰۵.docx'),'--output_dir',str(out/'rendered'),'--emit_pdf','--dpi','150']
module.main()
