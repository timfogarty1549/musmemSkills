<?php
findDups( 'bb_male.dat' );
findDups( 'bb_female.dat' );
exit();

function findDups( $file_name ) {
	$file = file( $file_name );
	$out = fopen( $file_name.".out", "w" ) or die('cant open file');
	$prev = '';
	foreach( $file as $line ) {
		if( $prev == $line ) {
			echo "DUP $prev";
		} else {
			fwrite( $out, $line );
		}
		$prev = $line;
	}
	fclose( $out );
}

