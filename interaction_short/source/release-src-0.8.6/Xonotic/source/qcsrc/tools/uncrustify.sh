fix_function_types() {




	sed -e 's/)\([A-Za-z_]\)/) \1/g' "$@"
}

if [ -z "$UNCRUSTIFY_CONFIG" ]; then
	UNCRUSTIFY_CONFIG=`git rev-parse --show-toplevel`/qcsrc/uncrustify.cfg
fi

case "$#" in
	0)
		uncrustify --frag -c "$UNCRUSTIFY_CONFIG" |\
		fix_function_types
		;;
	*)
		uncrustify --replace --no-backup -c "$UNCRUSTIFY_CONFIG" "$@" ;\
		fix_function_types -i "$@"
		;;
esac
