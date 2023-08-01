if [[ $PY311 == 1 ]]
then
    mkdir -p ./pydoc
    touch ./pydoc/__init__.py
    cat <<EOF > ./pydoc/__init__.py
def get_doc(*args):
    return ''
EOF
    git apply python311.patch
fi
