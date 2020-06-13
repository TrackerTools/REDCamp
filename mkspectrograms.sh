#!/bin/bash

# about:      mkspectrograms.sh -- make spectrograms with SoX, using env_parallel if available
# version:    01
# depends:    bash, sox, basename, dirname
# recommends: env_parallel (GNU Parallel)
# usage:      $> mkspectrograms.sh [OPTION [ARGUMENT]]... [--] FLAC_OR_FOLDER [FLAC_OR_FOLDER]...

  ####################
### DEFAULT SETTINGS ###

## threads for env_parallel
threads="4"

## SoX spectrogram commands
full_spectrogram_command="-n remix 1 spectrogram -x 3000 -y 513 -z 120 -w Kaiser"
zoom_spectrogram_command="-n remix 1 spectrogram -x 500 -y 1025 -z 120 -w Kaiser" # -S 1:00 -d 0:02 # -S: start time, -d: duration

## zoomed spectrogram settings
zoom_start="3" # divisor used against track duration to set starting position of zoomed spectrograms
zoom_total="2" # length of zoomed spectrograms in seconds

## spectrogram title length limit
# (mostly just zoomed) titles may grow too long to fit within the width of a spectrogram, and then SoX will
# just omit them entirely. So counting backwards from the end, cut longer titles down to this many characters
full_title_length_limit=""
zoom_title_length_limit="85"  # leave unset ( eg: _limit="" -NOT- _limit="0" ) to ignore either limit

## homebrew bin -- for Mac users, Automator defaults to ignoring Homebrew (or /usr/local/bin and users' default PATH anyway)
homebrew_bin="/usr/local/bin"

## SoX spectrogram commands - DEFAULTS
#full_spectrogram_command="-n remix 1 spectrogram -x 3000 -y 513 -z 120 -w Kaiser"
#zoom_spectrogram_command="-n remix 1 spectrogram -x 500 -y 1025 -z 120 -w Kaiser" # -S 1:00 -d 0:02 # -S: start time, -d: duration

### DEFAULT SETTINGS ###
  ####################


## functions ##
_error () { printf >&2 '%sERROR%s: %s\n' $'\033[0;31m' $'\033[0m' "$@" ; }

_help () {
	printf '
Usage:
   %s [OPTION [ARGUMENT]]... [--] FLAC_OR_FOLDER [FLAC_OR_FOLDER]...

Options:
   -h, -H, --help              Print this help text.
   --                          End of options. Subsequent arguments treated as potential flacs.

   -t ARG, --threads ARG       Set the number of concurrent threads to "ARG" if env_parallel is detected.

   -F,     --full-only         Only create full sized spectrograms.
   -Z,     --zoom-only         Only created zoomed spectrograms.

   -f ARG, --full-title ARG    Set full spectrogram title length limit to "ARG".
   -z ARG, --zoom-title ARG    Set zoom spectrogram title length limit to "ARG".

   -s ARG, --zoom-start ARG    Set the zoomed-spectrogram-start-point-divisor to "ARG".
   -l ARG, --zoom-length ARG   Set the length in seconds of zoomed spectrograms to "ARG".

' "${0##*/}"
}

_spectrograms () { # takes -one- array index as argument
	# output dir
	[[ ! -d ${absolute_flac_dirs[$1]}/Spectrograms/ ]] &&
		if ! mkdir -p "${absolute_flac_dirs[$1]}"/Spectrograms/ ;then
			_error "Failure creating output folder '${absolute_flac_dirs[$1]##*/}/Spectrograms/'."
			_error "Aborting spectrogram creation for ${flac_filenames[$1]}."
			return 1
		fi

	local spectrogram_title="${absolute_flac_dirs[$1]##*/}/${flac_filenames[$1]}"

	# full spectrogram
	[[ $zoom_only != "1" ]] && {
		[[ -n $full_title_length_limit && ${#spectrogram_title} -gt $full_title_length_limit ]] && spectrogram_title="... ${spectrogram_title: -$full_title_length_limit}"
		if ! sox "${absolute_flacs[$1]}" $full_spectrogram_command \
			 -t "$spectrogram_title" \
			 -c "         ${flac_bit_depths[$1]} bit  |  ${flac_sample_rates[$1]} Hz  |  ${flac_durations[$1]%.*} sec" \
			 -o "${absolute_flac_dirs[$1]}"/Spectrograms/"${flac_filenames[$1]%.[Ff][Ll][Aa][Cc]}"-full.png
		then
			_error "Failure creating full spectrogram for '${absolute_flacs[$1]}'."
			local fail="1"
		fi
	}

	# zoomed spectrogram
	[[ $full_only != "1" ]] && {
		local start_zoom="$(( ${flac_durations[$1]%.*} / $zoom_start ))"
		local zoom_spectrogram_command="$zoom_spectrogram_command -S 0:$start_zoom -d 0:$zoom_total"

		[[ -n $zoom_title_length_limit && ${#spectrogram_title} -gt $zoom_title_length_limit ]] && spectrogram_title="... ${spectrogram_title: -$zoom_title_length_limit}"
		if ! sox "${absolute_flacs[$1]}" $zoom_spectrogram_command \
			 -t "$spectrogram_title" \
			 -c "         ${flac_bit_depths[$1]} bit  |  ${flac_sample_rates[$1]} Hz  |  $zoom_total sec  |  starting @ $start_zoom sec" \
			 -o "${absolute_flac_dirs[$1]}"/Spectrograms/"${flac_filenames[$1]%.[Ff][Ll][Aa][Cc]}"-zoom.png
		then
			_error "Failure creating zoomed spectrogram for '${absolute_flacs[$1]}'."
			local fail="1"
		fi
	}

	[[ $fail -eq "1" ]] && return 1
}


## runtime options ##
while true ;do
	case "$1" in
		-f|--full-title)
			full_title_length_limit="$2"
			shift 2
			;;
		-F|--full-only)
			full_only="1"
			shift
			;;
		-h|-H|--help)
			_help ;exit 0
			;;
		-l|--zoom-length)
			zoom_total="$2"
			shift 2
			;;
		-s|--zoom-start)
			zoom_start="$2"
			shift 2
			;;
		-t|--threads)
			threads="$2"
			shift 2
			;;
		-z|--zoom-title)
			zoom_title_length_limit="$2"
			shift 2
			;;
		-Z|--zoom-only)
			zoom_only="1"
			shift
			;;
		--)
			break
			;;
		-?*)
			_error "Unknown option: '$1'" ;_help ;exit 1
			;;
		*)
			break
			;;
	esac
done
[[ $full_only == "1" && $zoom_only == "1" ]] && unset full_only zoom_only


## etc ##
[[ $# -lt "1" ]] && { _error "Nothing to do, please specify at least one flac file or folder. Use '--help' switch for more info." ;exit 1 ; }
[[ $PATH != *"$homebrew_bin"* ]] && PATH=$PATH:"$homebrew_bin"
pwd="$PWD"


## flac/folder arguments ##
shopt -s nullglob
for arg in "$@" ;do
	if [[ -d $arg ]] ;then
		flacs+=( "$arg"/*.[Ff][Ll][Aa][Cc] )
	elif [[ $arg == *.[Ff][Ll][Aa][Cc] ]] ;then
		flacs+=( "$arg" )
	fi
done
shopt -u nullglob
[[ ${#flacs[@]} -lt "1" ]] && { _error "No flac files found, aborting. Use '--help' switch for more info." ;exit 1 ; }
for flac in "${flacs[@]}" ;do
	# can I get a reliable dupe-check without using realpath to fancify absolute paths first?
	if [[ ${flac:0:1} = "/" ]] ;then absolute_flacs+=( "$flac" ) ;else absolute_flacs+=( "${pwd}/${flac}" ) ;fi
done


## making arrays
for index in "${!absolute_flacs[@]}" ;do
	absolute_flac_dirs[$index]="$( dirname    "${absolute_flacs[$index]}" )"
	    flac_filenames[$index]="$( basename   "${absolute_flacs[$index]}" )"
	   flac_bit_depths[$index]="$( sox --i -b "${absolute_flacs[$index]}" )"
	 flac_sample_rates[$index]="$( sox --i -r "${absolute_flacs[$index]}" )"
	    flac_durations[$index]="$( sox --i -D "${absolute_flacs[$index]}" )"
done


## run that motherfuckin' rhythm 'cause we're ready
if command -v env_parallel > /dev/null 2>&1 ;then
	. "$( which env_parallel.bash )" # setup env_parallel... aaand apparently that's it, if you're not worried about a too-big environment?
	env_parallel --will-cite -j "$threads" _spectrograms ::: "${!absolute_flacs[@]}"
else
	for index in "${!absolute_flacs[@]}" ;do
		_spectrograms "$index"
	done
fi