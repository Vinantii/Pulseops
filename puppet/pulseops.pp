file { '/opt/pulseops':
  ensure => directory,
  owner  => 'root',
  group  => 'root',
  mode   => '0755',
}

file { '/opt/pulseops/managed-by-puppet.txt':
  ensure  => file,
  content => "PulseOps configuration managed by Puppet.\n",
  owner   => 'root',
  group   => 'root',
  mode    => '0644',
  require => File['/opt/pulseops'],
}
